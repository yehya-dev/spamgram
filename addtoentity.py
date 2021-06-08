from os import system, mkdir
from pathlib import Path
import csv
from datetime import datetime, timedelta, timezone
import asyncio
import random


# Telethon Imports
from telethon import TelegramClient
from telethon.errors import UserBannedInChannelError, PeerFloodError, UserDeactivatedError, UserIdInvalidError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import InputPeerUser, UserStatusOnline, UserStatusRecently, UserStatusEmpty
from telethon.tl.types import UserStatusOffline, UserStatusLastWeek, UserStatusLastMonth
from colorama import Fore
from telethon.tl.functions.channels import InviteToChannelRequest

# Exceptions
from .exceptions import FileNotFound, AdminAccountNotAuthorized, AdminAccountNotFound, AccountListExhausted
# Types
from .types import EntityType

class Telegram_Add:

    def __init__(self, add_to_entity,
            unique_slug,
            entity_type=EntityType.CHANNEL,
            sleep_time_range=(60 * 5, 60 * 7),
            ) -> None:
        
        self.add_to_entity: str = add_to_entity
        self.entity_type: str = entity_type
        self.sleep_time_range: tuple = sleep_time_range

        self.admin_account_file = self.get_full_path(f'admin_account_{unique_slug}.csv')
        self.blacklist_file = self.get_full_path(f'blacklist_{unique_slug}.csv')
        self.collect_groups_file = self.get_full_path(f'add_group_{unique_slug}.csv')
        self.fake_accounts_file = self.get_full_path(f'accounts.csv')
        self.banned_account_file = self.get_full_path(f'bannedac_{unique_slug}.csv')
        self.sessions_dir = self.get_full_path('sessions')


        if not self.collect_groups_file.is_file():
            raise FileNotFound(f'{self.collect_groups_file} was not found or cannot be read')

        if not self.fake_accounts_file.is_file():
            raise FileNotFound(f'{self.fake_accounts_file} was not found or cannot be read')

        self.users_data_dir =  self.get_full_path(f'users_data/{unique_slug}')
        self.all_clients : dict = {}
        self.blacklist =  set()
        self.all_clients = self.get_clients()
        self.connect_all_clients()
        blacklist_file = open(self.blacklist_file, 'a', newline='', buffering=1)    
        self.blacklist_writer = csv.writer(blacklist_file)
        banned_account_file = open(self.banned_account_file, 'a', newline='', buffering=1)
        self.banned_account_writer = csv.writer(banned_account_file)
        self.lock_list = set()  # To lock a member to add to a particular account so that the next account won't select the same account
        self.temp_store_list = dict()

        self.admin_account = None
        if self.entity_type == EntityType.CHANNEL:
            loop = asyncio.get_event_loop()
            self.admin_account = loop.run_until_complete(self.get_admin_account())


    def connect_all_clients(self):
        asyncio.get_event_loop().run_until_complete(self.connect_clients())


    async def add_all_members_admins(self):
        for user in self.all_clients.values():
            user_obj = await user.get_me()
            user_id = user_obj.id
            await self.admin_account.edit_admin(
                self.add_to_entity,
                user_id,
                change_info=False,
                post_messages=False,
                edit_messages=False,
                delete_messages=False,
                ban_users=False,
                invite_users=True,
                pin_messages=False,
                manage_call=False,
                add_admins=False )

    
    def start(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.add_entity_members_blacklist())
        
        if self.admin_account and self.entity_type == EntityType.CHANNEL:
            print('Giving perms for everyone')
            loop.run_until_complete(self.add_all_members_admins())

        self.add_blacklist_file_members_to_blacklist()
        loop.run_until_complete(self._get_entity_memebers_and_start())

    
    async def get_admin_account(self):
        with open(self.admin_account_file) as adminfile:
            reader = csv.reader(adminfile)
            try:
                phone, api_id, api_hash = next(reader)
                print(f'Found Admin Account {phone}')
                api_id = int(api_id)
                client = TelegramClient(str(self.sessions_dir / phone), api_id, api_hash)
                await client.connect()
                if not await client.is_user_authorized():
                    raise AdminAccountNotAuthorized(f'Admin account with phone : {phone} is not authorized')
                return client
            except StopIteration:
                raise AdminAccountNotFound(f'Admin account not found in file {self.admin_account_file}')


    def create_dirs_and_files(self):
        not self.blacklist_file.is_file() and open(self.blacklist_file, 'w')
        not self.collect_groups_file.is_file() and open(self.collect_groups_file, 'w')
        not self.fake_accounts_file.is_fife() and open(self.fake_accounts_file, 'w')
        not self.banned_account_file.is_file() and open(self.banned_account_file, 'w')
        not self.admin_account_file.is_file() and open(self.admin_account_file, 'w')
        not self.users_data_dir.is_dir() and mkdir(self.users_data_dir)


    def get_banned_accounts(self) -> set:
        banned_accounts = set()
        if self.banned_account_file.is_file():
            with open(self.banned_account_file) as bannedacfile:
                banned_reader = csv.reader(bannedacfile)
                for ac in banned_reader:
                    banned_accounts.add(ac[0])  
        return banned_accounts


    def get_clients(self):
        banned_accounts = self.get_banned_accounts()

        all_clients = {}
        with open(self.fake_accounts_file) as accounts:
            reader = csv.reader(accounts)
            for account_data in reader:
                number = account_data[0]
                if number in banned_accounts:
                    print(f'{number} was found in banned list, skipping!')
                    continue
                all_clients[number] = self.create_client(account_data)
        return all_clients  


    def create_client(self, account_data):
            number = account_data[0]
            api_id = int(account_data[1])
            api_hash = account_data[2]
            print(f'Create Client -- {number}')
            client = TelegramClient(str(self.sessions_dir / number), api_id, api_hash)
            return client
        

    async def connect_clients(self):
        await asyncio.gather(
            *(self._connect_client(phone) for phone in self.all_clients)
            )


    async def _connect_client(self, phone):
        client = self.all_clients[phone]
        await client.connect()
        if not await client.is_user_authorized():
            with open(self.banned_account_file, 'a', newline='') as banned_ac_file:
                writer = csv.writer(banned_ac_file)
                writer.writerow([phone, datetime.now().strftime("%m/%d/%Y %H:%M:%S"), 'PhoneNumberBanned'])
            self.message('red', f'{phone} not authorized / banned from telegram')
        await client(JoinChannelRequest(self.add_to_entity))


    async def _get_entity_memebers_and_start(self):
        await asyncio.gather(
            *(self.fetch_data_and_start(phone) for phone in self.all_clients)
            )


    async def fetch_data_and_start(self, phone):
        client = self.all_clients[phone]
        if not self.users_data_dir.is_dir():
            mkdir(self.users_data_dir)
        user_data_file = self.users_data_dir / f'{phone}_data.csv'
        if not user_data_file.is_file():
            await self.collect_data(client, self._get_data_groups_list(), user_data_file, phone)
        
        await self.add_process(phone)
        

    async def collect_data(self, client : TelegramClient, group_list, filename, number):
        print(f'collecting data for {number}')
        all_participants = []
        for chan_link in group_list:
            print(f'fetching from {chan_link}')
            channel = await client.get_entity(chan_link)
            async for part in client.iter_participants(channel, limit=None, aggressive=True):
                if not part.bot:
                    all_participants.append(part)
            print('sleeping for 15 seconds')
            await asyncio.sleep(15)
            print('woke up!')

        current_utc_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        all_participants_sorted = sorted(all_participants, key= lambda user: self._user_last_seen_value(user, current_utc_time), reverse=True)
        with open(filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, dialect='excel')
            for part in all_participants_sorted:
                writer.writerow([part.id, part.access_hash, part.username, part.status])


    def _get_data_groups_list(self):
        group_list = []
        with open(self.collect_groups_file) as group_list_file:
            reader = csv.reader(group_list_file)
            for item in reader:
                group_list.append(item[0])
        return group_list


    def _user_last_seen_value(self, user, current_utc_time):
        last_seen_comparison = {
            UserStatusOnline: current_utc_time,
            UserStatusRecently: current_utc_time - timedelta(seconds=2),
            UserStatusLastWeek: current_utc_time - timedelta(weeks=1.5),
            UserStatusLastMonth: current_utc_time - timedelta(weeks=5),
            UserStatusEmpty: current_utc_time - timedelta(weeks=24),
            type(None): current_utc_time - timedelta(weeks=24)
        }
        status = user.status
        if type(status) == UserStatusOffline:
            return status.was_online
        else:
            return last_seen_comparison[type(status)]


    async def add_entity_members_blacklist(self):
        # Only channel admins can get the channel members list when adding to a channel, so we need to get the admin account
        temp_client = self.get_a_client(self.all_clients)
        print(f'getting {self.add_to_entity} channel members list')
        try:
            channel = await temp_client.get_entity(self.add_to_entity)
        except UserDeactivatedError:
            self.message('red', f'user deactivated')

        async for participant in temp_client.iter_participants(channel, limit=None, aggressive=True):
            print(participant.id, participant.access_hash, participant.first_name)
            self.blacklist.add(participant.id)


    def add_blacklist_file_members_to_blacklist(self):
        if self.blacklist_file.is_file():
            with open(self.blacklist_file) as csvfile:
                reader = csv.reader(csvfile)
                for item in reader:
                    self.blacklist.add(int(item[0]))


    def get_full_path(self, partial_path):
        return Path.joinpath(Path(__file__).parent, partial_path)
        

    def message(self, msg_color, string):
        print(Fore.__getattribute__(msg_color.upper()) + string + Fore.RESET)


    def get_a_client(self, all_clients, client_count=1):
        """
        returns {client_count}'th client from the all_clients dictionary if 
        {self.admin_account} is not present, else return self.admin_account
        """

        if self.admin_account:
            return self.admin_account

        for count, client in enumerate(all_clients, start=1):
            if count == len(all_clients):
                return all_clients[client]
            elif count == client_count:
                return all_clients[client]

    def get_next_user(self, reader):
        try:
            return next(reader)
        except StopIteration:
            return False

    async def add_process(self, phone):
        client = self.all_clients[phone]
        csv_file = open(self.users_data_dir / f'{phone}_data.csv', 'rt')
        reader = csv.reader(csv_file)
  
        while True:
            got_user_from_templist = False
            if temp_list := self.temp_store_list.get(phone):
                for item in temp_list:
                    if item[0] not in self.lock_list and item[0] not in self.blacklist:
                        user = item
                        got_user_from_templist = True
                        print("Item got from temp_list", item)
                        temp_list.remove(user)
                        break
            
            if not got_user_from_templist:
                user = self.get_next_user(reader)
                if not user:
                    break

            user_id = int(user[0])
            user_hash = int(user[1])
            username = user[2]
            
            if user_id in self.blacklist:
                print(f'{phone} >> user {user_id} was in skip list, skipping')
                continue
            elif user_id in self.lock_list:
                print(f'{phone} >> user {user_id} was in lock list, skipping')

                if phone in self.temp_store_list:
                    self.temp_store_list[phone].append((user_id, user_hash, username))
                else:
                    self.temp_store_list[phone] = [(user_id, user_hash, username)]

                continue

            self.lock_list.add(user_id)
            user_to_add = InputPeerUser(user_id, user_hash)

            try:
                print(f'Tring to add user {user_id}')
                channel = await client.get_entity(self.add_to_entity)
                await client(InviteToChannelRequest(
                    channel,
                    [user_to_add]
                ))
                self.message('green', f'{phone} Adding User {user_id} Success')

            except (PeerFloodError, UserBannedInChannelError) as e:
                self.message('red', f'{e} for {phone}')
                self.lock_list.remove(user_id)
                print("Removing exception raised account and adding to banned list")
                self.all_clients.pop(phone)
                # TODO Make the banned list stored in memory if the script is run for really long times and banned accounts might
                # have to be loaded back during the same runtime.
                # if i am implementing a try a banned account after a particular amount of time after it's banned
                self.banned_account_writer.writerow([phone, datetime.now().strftime("%m/%d/%Y %H:%M:%S"), type(e).__name__])
                try:
                    await self.try_unblock(client)
                except Exception as e:
                    self.message('Magenta', str(e))
                return False

            except UserIdInvalidError:
                print(f"{phone} couldn't add this member, ID/HASH mismatch")

            except Exception as e:
                error_user = [user_id, user_hash, username, phone, str(e) + type(e).__name__]
                self.add_to_blacklist(error_user)
                self.message('yellow', f'{phone} Added fail_log : {error_user}')
            else:
                added_user = [user_id, user_hash, username, phone, "Added to entity ig"]
                self.add_to_blacklist(added_user)


            print('All client count', len(self.all_clients))
            self.lock_list.remove(user_id)
            if len(self.all_clients) == 0:
                raise AccountListExhausted('No users available for the process')


            sleep_base = self.sleep_time_range[0]
            sleep_ceil = self.sleep_time_range[1]
            sleep_time = random.randint(sleep_base, sleep_ceil)

            self.message('cyan', f'{phone} sleeping for {sleep_time} seconds')
            await asyncio.sleep(sleep_time)
            print(f'{phone} -- Awake')


    def add_to_blacklist(self, data):
        self.blacklist_writer.writerow(data)
        self.blacklist.add(data[0])


    async def try_unblock(self, client):
        needed_replies = ['But I can’t message non-contacts!', 'No, I’ll never do any of this!']
        spambot = await client.get_entity('@SpamBot')
        await client.send_message(spambot, '/start')
        for _ in range(2):
            spambot_messages = await client.get_messages(spambot)
            message = spambot_messages[0]
            await asyncio.sleep(3)
            for row in message.reply_markup.rows:
                for button in row.buttons:
                    if button.text in needed_replies:
                        await client.send_message(spambot,button.text)
                        break
        await asyncio.sleep(3)
        await client.send_message(spambot, "Can only add mutual contacts to the group.")



# TODO Create The Ability to add fake accounts, admin accounts, banned_list etc from the code
# TODO Change Data Storage to a sqlite database / someother database
# TODO Make everything more modular and simple
# TODO Enable Logging Errors in file and not in STDOUT