
def fibo(n):
    if n <= 1:
        return 1
    return fibo(n - 1) + fibo(n - 2)


def main() -> None:
    """Utilise la navigation commune pour les lancements locaux et hébergés."""
    from projet_sncf.main import run_app

    run_app()


if __name__ == "__main__":
    main()

