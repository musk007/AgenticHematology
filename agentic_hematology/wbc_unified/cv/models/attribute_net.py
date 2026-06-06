"""EfficientNet-based multi-label attribute classifier on cell crops."""
from __future__ import annotations

import torch
import torch.nn as nn
from torchvision import models


class AttributeNet(nn.Module):
    def __init__(self, num_attrs: int = 6, backbone: str = "efficientnet_b0", pretrained: bool = True):
        super().__init__()
        self.num_attrs = num_attrs
        weights = "DEFAULT" if pretrained else None
        if backbone == "efficientnet_b0":
            enc = models.efficientnet_b0(weights=weights)
            feat_dim = enc.classifier[1].in_features
            enc.classifier = nn.Identity()
            self.encoder = enc
        elif backbone == "resnet18":
            enc = models.resnet18(weights=weights)
            feat_dim = enc.fc.in_features
            enc.fc = nn.Identity()
            self.encoder = enc
        else:
            raise ValueError(f"Unknown backbone: {backbone}")

        self.head = nn.Sequential(
            nn.Linear(feat_dim, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, num_attrs),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.encoder(x))


def build_attribute_model(
    num_attrs: int = 6,
    backbone: str = "efficientnet_b0",
    pretrained: bool = True,
) -> AttributeNet:
    return AttributeNet(num_attrs=num_attrs, backbone=backbone, pretrained=pretrained)


def masked_bce_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    pos_weight: torch.Tensor | None = None,
) -> torch.Tensor:
    """logits/targets: (B, A); targets in {0,1} with -1 for ignore."""
    mask = targets >= 0
    if not mask.any():
        return logits.sum() * 0.0
    t = targets.clamp(min=0, max=1).float()
    pw = pos_weight.view(1, -1) if pos_weight is not None else None
    loss = nn.functional.binary_cross_entropy_with_logits(
        logits, t, pos_weight=pw, reduction="none"
    )
    loss = loss * mask.float()
    return loss.sum() / mask.float().sum().clamp(min=1.0)
