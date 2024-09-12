import discord
from discord.ext import commands
import subprocess
import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not TOKEN:
    sys.stderr.write("Error: DISCORD_BOT_TOKEN environment variable not found!\n")
    sys.exit(1)

# This is used in case multiple tasks are being run
bash_tasks = {}

async def execute_bash_script(script, channel):
    # Clean input
    if script.startswith("```bash") and script.endswith("```"):
        script = script[7:-3].strip()

    # Execute script
    process = subprocess.Popen(
        ["/bin/bash", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # This reads the std output and sends to the chat
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            await channel.send(output.strip())

    process.wait()
    await channel.send("Script execution completed!")
    print('done')


@bot.event
async def on_message(message):
    global bash_tasks

    if message.author == bot.user:
        return

    if message.content.startswith("!bash"):
        print("Starting bash execution")
        
        script = message.content[len("!bash"):].strip()

        # Clean input
        if script.startswith("```bash") and script.endswith("```"):
            script = script[7:-3].strip()

        await message.channel.send(f"{message.author.name}, your bash script is being executed...")

        # Add a new task for parallel processing
        task_key = (message.channel.id, message.author.id)

        # Cancel any previous bash task
        if task_key in bash_tasks and not bash_tasks[task_key].done():
            bash_tasks[task_key].cancel()
            await message.channel.send(f"{message.author.name}, your previous task was canceled.")

        # Create a new bash task
        bash_tasks[task_key] = asyncio.create_task(execute_bash_with_timeout(script, message.channel, message.author.name))

    elif message.content.startswith("!cancel"):
        task_key = (message.channel.id, message.author.id)
        if task_key in bash_tasks and not bash_tasks[task_key].done():
            bash_tasks[task_key].cancel()
            await message.channel.send(f"{message.author.name}, your bash script execution has been canceled!")
        else:
            await message.channel.send(f"{message.author.name}, you have no running bash script to cancel.")

async def execute_bash_with_timeout(script, channel, user_name):
    try:
        await asyncio.wait_for(execute_bash_script(script, channel), timeout=300)
    except asyncio.TimeoutError:
        await channel.send(f"{user_name}, your bash script timed out after 5 minutes!")
    except asyncio.CancelledError:
        await channel.send(f"{user_name}, your bash script execution was canceled.")
    except Exception as e:
        await channel.send(f"An error occurred: {str(e)}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}.")

bot.run(TOKEN)
