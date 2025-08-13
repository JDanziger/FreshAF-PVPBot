# -*- coding: utf-8 -*-
import logging
logging.basicConfig(filename='log.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger('Info')
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ChatJoinRequestHandler
import json 
import pvp_poll
import re
import database
import requests
import trainernames
import language_support as lan
import response_menu
pvprequests = {}
competitors = {}

""" Load the token that we use to communicate with our bot """
with open('config.json') as json_config_file:
    config = json.load(json_config_file)
""" Load the responses by our bot for each languages """
responses = lan.responses
""" Load the currently supported languages """
supported_languages = lan.supported_languages

""" Initialise our Telegram tools"""    
updater = Updater(config['token'], use_context=True)
job = updater.job_queue
dispatcher = updater.dispatcher

""" 
This part until start is just an easter egg
"""
def get_dog():
    contents = requests.get('https://random.dog/woof.json').json()
    url = contents['url']
    return url

def get_cat():
    contents = requests.get('https://api.thecatapi.com/v1/images/search').json()
    url = contents['file']
    return url

def get_joey():
    contents = requests.get('http://aws.random.cat/meow').json()
    url = contents['file']
    return url

def get_image_url(pic):
    allowed_extension = ['jpg','jpeg','png']
    file_extension = ''
    while file_extension not in allowed_extension:
        if pic == 'cat':
            url = get_cat()
        elif pic == 'dog':
            url = get_dog()
        else:
            url = get_joey()

        file_extension = re.search("([^.]*)$",url).group(1).lower()
    return url

def meow(update, context):
    url = get_image_url('cat')
    context.bot.send_photo(chat_id=update.message.chat_id, photo=url)    

def bop(update, context):
    url = get_image_url('dog')
    context.bot.send_photo(chat_id=update.message.chat_id, photo=url)

def joey(update, context):
    url = get_image_url('dog')
    context.bot.send_photo(chat_id=update.message.chat_id, photo=url)

""" 
Send the start message to a user is he starts the bot. This message is also sent 
when a user types /help
"""
def start(update, context):
    language = database.get_language(update.message.chat_id)
    response = ''
    response = response.join(responses[language]['start'])
    context.bot.send_message(parse_mode='Markdown', chat_id=update.message.chat_id, text=response)    

"""
Change the language setting of a group/user
"""
def language(update, context):
    logger.info('Language query by %s with query %s', update._effective_user.username, context.args)
    #Make sure that we only handle messages that we can speak
    language = database.get_language(update.message.chat_id)
    if update.message.chat_id < 0:
        admins = (admin.user.id for admin in context.bot.get_chat_administrators(update.message.chat.id))     
        if update._effective_user.id not in admins:
            response = responses[language]['only_for_admins']
            bot_message = context.bot.send_message(parse_mode='Markdown', chat_id=update.message.chat_id, text=response)
            return 
        
    if len(context.args) == 1 and context.args[0].lower() in supported_languages:
        database.toggle_groups(update, context, 'Language')
    #If we reject the input we try to delete the users message and let him know which languages we speak
    else:
        #Get the language that we are speaking in this group and tell the user which languages we can speak
        response = responses[language]['language_not_supported']
        response = response.format(supported_languages)
        bot_message = context.bot.send_message(parse_mode='Markdown', chat_id=update.message.chat_id, text=response)


"""
Deletes a message 
Called as a job which is executed with some delay to enable the user to read the response
"""
def delete_message(context):
    try:
        context.bot.delete_message(chat_id=context.job.context[0], message_id=context.job.context[1])
        logger.info("Deleted message %s %s", context.job.context[0], context.job.context[1])
    except:
        logger.info("Cannot delete message %s %s", context.job.context[0], context.job.context[1])


def main():
    logger.info('Started bot')

    #Easter egg commands
    dispatcher.add_handler(CommandHandler('pbp',bop))
    dispatcher.add_handler(CommandHandler('pcp',meow))
    dispatcher.add_handler(CommandHandler('joey',joey))

    #/start and /help to give the introduction
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))

    #Show Version
    updater.dispatcher.add_handler(CommandHandler('version', pvp_poll.version))
    #Create a pvp request
    updater.dispatcher.add_handler(CommandHandler('pvp', pvp_poll.pvp))
    #Add/removes a competitor if he clicks on fight
    updater.dispatcher.add_handler(CallbackQueryHandler(pvp_poll.add_competitor, pattern='fight'))
    #Remove player from poll (Leave Option)
    updater.dispatcher.add_handler(CallbackQueryHandler(pvp_poll.remove_competitor, pattern='leave'))
    #Deletes a pvp request - TODO: Admins should be able to delete requests
    updater.dispatcher.add_handler(CallbackQueryHandler(pvp_poll.delete_poll, pattern='delete'))
    #Check if there are any outdated pvp requests which we want to delete
    auto_del = job.run_repeating(pvp_poll.auto_delete, interval=300, first=0)
    float_poll = job.run_repeating(pvp_poll.float_poll, interval=120, first=0)

    #Confirm config request
    updater.dispatcher.add_handler(CallbackQueryHandler(response_menu.confirm_config, pattern='Confirm'))

    #This handles config changes
    updater.dispatcher.add_handler(CallbackQueryHandler(response_menu.update_response))
    
    #Handle /language
    dispatcher.add_handler(CommandHandler("language", language))    

    #Set trainername and trainercode
    dispatcher.add_handler(CommandHandler("trainername", trainernames.add_trainername))
    dispatcher.add_handler(CommandHandler("trainercode", trainernames.add_trainercode))


    #This is the last method and should be used to refer to info
    #unknown_handler = MessageHandler(Filters.command, unknown)
    #dispatcher.add_handler(unknown_handler)    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()