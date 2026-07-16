from app.security import generate_api_key


def main() -> None:
    key, hashed = generate_api_key("aq_live_")
    print("New API key (shown once):")
    print(key)
    print()
    print("Store this hash in AQUASTAT_API_KEY_HASHES:")
    print(hashed)


if __name__ == "__main__":
    main()
