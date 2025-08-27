import asyncio
import sys
import time
from ipaddress import IPv4Network, IPv6Network, ip_network
from pathlib import Path
from typing import Final

import httpx
import typer
from more_itertools import partition
from pyroute2.netlink.nfnetlink.nftsocket import NFPROTO_INET
from pyroute2.nftables.main import AsyncNFTables
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


async def nft_add_prefixes(prefixes: set[str], table: str, ipv4set: str, ipv6set: str) -> bool:
    networks = map(ip_network, prefixes)
    ipv4nets, ipv6nets = map(list, partition(lambda network: network.version == 4, networks))

    async with AsyncNFTables(nfgen_family=NFPROTO_INET) as nft:
        result = await nft.set_elems(
            "add", table=table, set=ipv4set, elements=ipv4nets
        )
        print(result)
        result = await nft.set_elems(
            "add", table=table, set=ipv6set, elements=ipv6nets
        )
        print(result)

    return True


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

    success = asyncio.run(nft_add_prefixes(prefixes, table, ipv4set, ipv6set))
    sys.exit(0 if success else 1)
