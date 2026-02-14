from discord.ext import commands
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
import numpy as np
from .variables import magical_characters

load_dotenv()

search_tool  = TavilySearch(max_results = 10, topic="general")
system_message = SystemMessage(content="You will be assigned a character from the fictional series \"Harry Potter\"."
            "You will impersonate the character, and respond to the given prompt as the character would. Your response should not be verbose."
            "It should be no longer than 5 sentences. End the response by signing off as the character."
            "Use search_tool to augment responses for accuracy and clarity."
            )
wisher_agent = create_agent(
    model=ChatOpenAI(
        model="openrouter/auto",
        base_url="https://openrouter.ai/api/v1"
    ),
    tools=[search_tool],
    system_prompt=system_message
)
async def wish_creator():
    character = np.random.choice(magical_characters)
    human_message = {"messages":HumanMessage(content=f"Wish the user a happy birthday as {character}.")}
    model_response = await wisher_agent.ainvoke(
        input=human_message
    )
    response = model_response["messages"][-1]
    print(f"wish generated with model{response.response_metadata.get("model_name")}")
    ai_response = response.content.strip()
    return ai_response

async def setup(bot: commands.Bot):
    pass