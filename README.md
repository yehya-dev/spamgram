# SpamGram
## Python Package For Marketing And Building Audience On Telegram, Build With Python 3.8 

___
### Notes

**Use Example**<br>
*To add a lot of members to a group / channel from another group*

1. Clone the repo
2. `pip install -r requirements.txt`
3. Create a python file `test.py` (like the tree below)
    ```
    ├── spamgram
    │   ├── addtoentity.py
    │   ├── exceptions.py
    |   .
    |   .
    |
    ├── test.py
    ```
4. Add the below code to `test.py`
   ```py
    # test.py
    from spamgram  import Telegram_Add, EntityType
    
    # add_to_entity -> Telegram Group / Channel link
    # entity_type -> EntityType.CHANNEL / EntityType.Group 
    # unique_slug -> A filename friendly name for the project 
    #    ex : my_group_telegram
    # Don't have same name for two different projects (This will overwrite the data of the previous project)
    
    my_group_proj = Telegram_Add(add_to_entity, entity_type, unique_slug)
    my_group_proj.start()
    # The above line will create all the required directories and files inside spamgram directory.
   ```
   You'll need to add the data required as metioned below to the respective files
   ```
     1) accounts.csv (Info of the accounts use)
        format : 
         phone_number, api_id , api_hash
         ..
         ..


     2) admin_account_{unique_slug}.csv (Info the admin account of the channel/group to add to, only required if adding to a channel)
        format : 
        phone_number, api_id, api_hash
        ..
        ..


     3) add_group_{unique_slug}.csv (Info about groups to fetch memebers from)
        format :
        telegram_group_link
        ..
        ..
    

     4) blacklist_{unique_slug}.csv (Info of memebers to avoid)
        format : 
        user_id,,user_name(optional),,note(optional)
        (note the multiple commas)
   ```
   ```py
   # Now to start the process by pressing enter 

   ```

### Features
1. Multiple Accounts Can Be Added (These Accounts Will Be Used Within Certain Intervals To Avoid Accounts Getting Banned)
2. Automatic Account Switching
3. Account Temporarly Disabled If Server Returns A Warning
4. Try To Unblock An Account Automatically If Warning Is Raised

*The more the number of accounts used, the better*

### Dependencies
- colorama==0.4.3
- Telethon==1.21.1
