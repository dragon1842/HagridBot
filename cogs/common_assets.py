import numpy as np
import os
from pathlib import Path

bot_testing = 1068409137605656676
clock_tower = 825789506019000320
great_hall = 1510350950882218245

guild_id = 524552788932558848

professors = 731429277563748412

dragon = 876529458880847892

alert_emoji = "<a:alert:1415015206895091833>"
approve_tick_emoji = "<a:approve_tick:1415015152427728937>"

magical_characters = np.array(["Albus Dumbledore", "Minerva McGonagall", "Oliver Wood", "Percy Weasley", "Remus Lupin", 
                      "Sirius Black", "Molly Weasley", "Arthur Weasley", "Professor Sprout", "Newt Scamander", 
                      "Nymphadora Tonks", "Fillius Flitwick", "Gilderoy Lockhart", "Helena Ravenclaw", 
                      "Lord Voldermort", "Lucius Malfoy", "Bellatrix Lestrange", "Dolores Umbridge", 
                      "Severus Snape", "Horace Slughorn", "Rubeus Hagrid", "Sybill Trewalney", "Alastor Moody", 
                      "Cedric Diggory", "Harry Potter", "Ron Weasley", "Hermione Granger", "Fred Weasley", "George Weasley", 
                      "Ginny Weasley", "Dobby", "Neville Longbottom", "Luna Lovegood", "Draco Malfoy", "Peeves",
                      "Nearly-Headless Nick"])

images_dir = Path(__file__).parent.parent / "images"
images = np.array(os.listdir(str(images_dir)))
from discord import app_commands
from discord.ext import commands

def owner_bypass_cooldown(rate, per):
    def factory(interaction):
        if interaction.user.id == dragon:
            return None
        return app_commands.Cooldown(rate, per)
    return app_commands.checks.dynamic_cooldown(factory, key=lambda i: i.user.id)
async def setup(bot: commands.bot):
    pass