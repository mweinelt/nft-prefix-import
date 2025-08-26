import typer

from nft_prefix_import import main


def cli():
    typer.run(main)


if __name__ == "__main__":
    cli()
