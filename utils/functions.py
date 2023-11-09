def safe_format(message: str, **kwargs) -> str:
    """A poorly written format function."""
    for key, value in kwargs.items():
        formatted_key = "{" + key + "}"
        message = message.replace(formatted_key, str(value))
    return message


def bold(message: str) -> str:
    return f"**{message}**"
