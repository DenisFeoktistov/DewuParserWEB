import logging


# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


parser_exceptions_logger = logging.getLogger('DewuParser')

parser_exceptions_logger.setLevel(logging.INFO)

parser_handler = logging.FileHandler('DewuParserExceptions.log')
parser_handler.setFormatter(formatter)

parser_exceptions_logger.addHandler(parser_handler)


main_logger = logging.getLogger('MainApp')

main_logger.setLevel(logging.INFO)

main_handler = logging.FileHandler('MainApp.log')
main_handler.setFormatter(formatter)

main_logger.addHandler(main_handler)
