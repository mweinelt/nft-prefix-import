import sys
import time
from ipaddress import ip_network
from pathlib import Path
from subprocess import CalledProcessError, run
from traceback import print_exc
from typing import Final

import httpx
import typer
from more_itertools import partition
from typing_extensions import Annotated


def get_rttable(user_agent: str) -> str:
    def fetch() -> str:
        url = "https://bgp.tools/table.txt"
        headers = {"User-Agent": user_agent}
        response = httpx.get(url, headers=headers)
        assert response.status_code == 200
        return response.text

    rttable_cache: Final = Path("./table.txt")

    try:
        mtime = rttable_cache.stat().st_mtime
    except FileNotFoundError:
        mtime = None

    # don't pull more often than every two hours
    if not mtime or time.time() - mtime > 2 * 3600:
        print("Pulling routing table from bgp.tools", file=sys.stderr)
        data = fetch()
        with rttable_cache.open("w") as fd:
            fd.write(data)
    else:
        print("Loading routing table from cache", file=sys.stderr)
        with rttable_cache.open() as fd:
            data = fd.read()

    return data


def nft_add_elements(
    prefixes: set[str], table: str, ipv4set: str, ipv6set: str
) -> None:
    networks = map(ip_network, prefixes)
    ipv4nets, ipv6nets = partition(lambda ip: ip.version == 6, networks)

    def add_elements(setname: str, elements: list[str]) -> None:
        run(
            [
                "nft",
                "add",
                "element",
                "inet",
                table,
                setname,
                "{",
                ", ".join(map(str, elements)),
                "}",
            ],
            check=True
        )
    try:
        add_elements(ipv4set, ipv4nets)
    except CalledProcessError:
        print_exc()

    try:
        add_elements(ipv6set, ipv6nets)
    except CalledProcessError:
        print_exc()


def main(
    autnums: Annotated[
        list[str], typer.Argument(help="List of autonomous systems (AS) numbers")
    ],
    user_agent: Annotated[str, typer.Option(envvar="USER_AGENT")],
    table: Annotated[str, typer.Option(help="Table in nftables to target")] = "filter",
    ipv4set: Annotated[
        str, typer.Option(help="Set for IPv4 prefixes")
    ] = "ipv4prefixes",
    ipv6set: Annotated[
        str, typer.Option(help="Set for IPv6 prefixes")
    ] = "ipv6prefixes",
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
    nft_add_elements(prefixes, table, ipv4set, ipv6set)
