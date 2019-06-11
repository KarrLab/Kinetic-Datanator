import configparser


class ServerUtil():
    '''Utility function to read authentication files
    for connection with MongoDB servers on AWS
    '''

    def __init__(self, config_file=None, username=None, password=None,
                 server = None, port=None, verbose=True):

        self.config_file = config_file
        self.username = username
        self.password = password
        self.port = port
        self.server = server
        self.verbose = verbose
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

    def get_admin_config(self):
        if self.verbose:
            print(self.config.sections())
        admin = self.config['admin']
        username = admin.get('User', self.username)
        password = admin.get('Password', self.password)
        server = admin.get('Server', self.server)
        port = admin.get('Port', self.port)

        return (username, password, server, port)
