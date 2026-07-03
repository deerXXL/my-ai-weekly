from github_trending import fetch_github_trending


def test():
    items = fetch_github_trending()

    for item in items:
        print(item)


if __name__ == "__main__":
    test()