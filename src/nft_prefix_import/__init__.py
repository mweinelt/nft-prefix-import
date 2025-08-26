import sys
import time
from ipaddress import ip_network
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import Final

import httpx
import typer
from typing_extensions import Annotated


def get_rttable(user_agent: str) -> str:
    def fetch() -> str:
        url = "https://bgp.tools/table.txt"
        headers = {"User-Agent": user_agent}
        response = httpx.get(url, headers=headers)
        assert response.status_code == 200
        return response.text

    RTTABLE_CACHE: Final = Path("./table.txt")

    try:
        mtime = RTTABLE_CACHE.stat().st_mtime
    except FileNotFoundError:
        mtime = None

    # don't pull more often than every two hours
    if not mtime or time.time() - mtime > 2 * 3600:
        print("Pulling routing table from bgp.tools", file=sys.stderr)
        data = fetch()
        with RTTABLE_CACHE.open("w") as fd:
            fd.write(data)
    else:
        print("Loading routing table from cache", file=sys.stderr)
        with RTTABLE_CACHE.open() as fd:
            data = fd.read()

    return data


def nft_block(prefixes: set[str], table: str, ipv4set: str, ipv6set: str) -> None:
    networks = map(ip_network, prefixes)

    for network in networks:
        try:
            run(
                [
                    "nft",
                    "add",
                    "element",
                    "inet",
                    table,
                    ipv4set if network.version == 4 else ipv6set,
                    "{",
                    str(network),
                    "}",
                ],
                check=True,
            )
        except CalledProcessError:
            continue


def main(
    autnums: Annotated[list[str], typer.Argument(help="List of autonomous systems (AS) numbers")],
    user_agent: Annotated[str, typer.Option(envvar="USER_AGENT")],
    table: Annotated[str, typer.Option(help="Table in nftables to target")] = "filter",
    ipv4set: Annotated[str, typer.Option(help="Set for IPv4 prefixes")] = "ipv4prefixes",
    ipv6set: Annotated[str, typer.Option(help="Set for IPv6 prefixes")] = "ipv6prefixes",
) -> None:
    rttable = get_rttable(user_agent)

    prefixes = set()
    for line in rttable.splitlines():
        try:
            prefix, autnum = line.split()
        except ValueError:
            continue
        if autnum in autnums:
            prefixes.add(prefix)
    nft_block(prefixes, table, ipv4set, ipv6set)
