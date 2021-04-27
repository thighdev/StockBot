from discord.embeds import Embed
from discord.colour import Colour


class Embedder:
    @staticmethod
    def error(message):
        embed = Embed(title="Error", description=message, colour=Colour.red())
        return embed

    @staticmethod
    def help(message):
        embed = Embed(title="Command Help", description=message, colour=Colour.purple())
        return embed

    @staticmethod
    def embed(title, message):
        embed = Embed(title=title, description=message, colour=Colour.green())
        return embed

    @staticmethod
    def approve(message):
        embed = Embed(description=message, colour=Colour.green())
        return embed
