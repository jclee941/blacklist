from ipaddress import ip_address, ip_network


class FortiGateTargetError(Exception):
    reason: str

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def parse_fortigate_target(value: str, allowed_networks: tuple[str, ...]) -> str:
    if not allowed_networks:
        raise FortiGateTargetError("FortiGate target policy is not configured")
    try:
        address = ip_address(value.strip())
        networks = tuple(ip_network(network, strict=False) for network in allowed_networks)
    except ValueError as error:
        raise FortiGateTargetError("FortiGate target is invalid") from error
    if not any(address in network for network in networks):
        raise FortiGateTargetError("FortiGate target is outside allowed networks")
    return str(address)
