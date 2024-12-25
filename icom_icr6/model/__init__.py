from . import _support
from ._support import ValidateError
from .channels import Bank, BankChannels, BankLinks, Channel, ChannelFlags
from .radio import RadioModel
from .scan import ScanEdge, ScanLink
from .settings import BandDefaults, RadioSettings

__all__ = [
    "BandDefaults",
    "Bank",
    "BankChannels",
    "BankLinks",
    "Channel",
    "ChannelFlags",
    "RadioModel",
    "RadioSettings",
    "ScanEdge",
    "ScanLink",
    "ValidateError",
]


def enable_debug() -> None:
    _support.DEBUG = True
