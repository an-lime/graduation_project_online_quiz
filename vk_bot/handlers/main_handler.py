from vkbottle.bot import Message
from vkbottle.framework.labeler import BotLabeler

main_labeler = BotLabeler()

@main_labeler.message()
async def echo(message: Message):
    message_text = message.text
    await message.reply(message_text)