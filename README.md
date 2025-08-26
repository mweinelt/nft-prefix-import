# nft-prefix-import

Tool to import prefixes for whole autonomous systems into nftables sets for
efficient matching in subsequent firewalling decisions.

## Usage

To use `nft-prefix-import` we source routing information from
<https://bgp.tools>. The terms say to not request data more often than every
two hours and to provide a useful user-agent where you can be contacted.

To that end the tool caches the downloaded routing information and reuses
the information for up to two hours before requesting new data.

```shell
$ nft-prefix-import --help
Usage: nft-prefix-import [OPTIONS] AUTNUMS...

Arguments:
  AUTNUMS...  List of autonomous systems (AS) numbers  [required]

Options:
  --user-agent TEXT  [env var: USER_AGENT; required]
  --table TEXT       Table in nftables to target  [default: filter]
  --ipv4set TEXT     Set for IPv4 prefixes  [default: ipv4prefixes]
  --ipv6set TEXT     Set for IPv6 prefixes  [default: ipv6prefixes]
  --help             Show this message and exit.
```

## Example

The following example shows a possible nftables structure, that works with the default settings.

```nft
table inet filter {
  set ipv4prefixes {
    type ipv4_addr;
    flags interval, timeout;
    auto-merge;
    timeout 12h;
  }
  set ipv6prefixes {
    type ipv6_addr;
    auto-merge;
    flags interval, timeout;
    timeout 12h;
  }
  chain input {
    type filter hook input priority filter;

    # other rules here

    # block access to https for selected autnums
    ip saddr @ipv4prefixes tcp dport 443 counter drop;
    ip6 saddr @ipv6prefixes tcp dport 443 counter drop;

    # other rules here
  }
}

```
 
