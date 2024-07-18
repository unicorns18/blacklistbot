from functools import lru_cache, wraps
from utils import logutils
import redis

logger = logutils.CustomLogger(__name__)

def cache_invalidation_on_user_change(func):
    @wraps(func)
    def wrapper(self, user_id, *args, **kwargs):
        result = func(self, user_id, *args, **kwargs)
        self.get_user.cache_clear()
        return result
    return wrapper

class RedisDB:
    def __init__(self, db=0):
        self.redis = redis.StrictRedis(connection_pool=redis.ConnectionPool(host='localhost', port=6379, db=db))

    @cache_invalidation_on_user_change
    def set_user(self, user_id, username, reason, proof_link, folder_id):
        """
        Sets the user information in a hash with fields for username, reason, proof link, and folder ID.
        """
        try:
            self.redis.hset(user_id, mapping={
                "username": username,
                "reason": reason,
                "proof_link": proof_link,
                "folder_id": folder_id
            })
        except redis.RedisError as e:
            logger.error(f"Error setting user {user_id} in the database: {e}")

    @lru_cache(maxsize=128)
    def get_user(self, user_id):
        """
        Retrieves all fields for a given user_id as a dictionary.
        """
        try:
            user_data = self.redis.hgetall(user_id)
            return {k.decode('utf-8'): v.decode('utf-8') for k, v in user_data.items()}
        except redis.RedisError as e:
            logger.error(f"Error getting user {user_id} from the database: {e}")
            return {}

    @cache_invalidation_on_user_change
    def delete_user(self, user_id):
        """
        Deletes a user entry by user_id.
        """
        try:
            self.redis.delete(user_id)
        except redis.RedisError as e:
            logger.error(f"Error deleting user {user_id} from the database: {e}")

    def list_all_users(self):
        """
        Lists all user_ids in the database.
        """
        try:
            return [key.decode('utf-8') for key in self.redis.scan_iter("*")]
        except redis.RedisError as e:
            logger.error(f"Error listing all users from the database: {e}")
            return []

    def list_all_users_info(self):
        """
        Lists all users and their associated information from the database.
        """
        users = self.list_all_users()
        all_user_data = {}
        try:
            with self.redis.pipeline() as pipeline:
                for user_id in users:
                    pipeline.hgetall(user_id)
                results = pipeline.execute()
                
                for user_id, user_data in zip(users, results):
                    all_user_data[user_id] = {k.decode('utf-8'): v.decode('utf-8') for k, v in user_data.items()}
        except redis.RedisError as e:
            logger.error(f"Error listing all users and their information from the database: {e}")
        return all_user_data

    def search_users(self, pattern):
        """
        Searches for users by matching a pattern in the username field.
        """
        matched_data = []
        try:
            users = self.list_all_users()
            for user_id in users:
                username = self.redis.hget(user_id, "username").decode('utf-8')
                if pattern.lower() in username.lower():
                    user_data = self.get_user(user_id)
                    matched_data.append((user_id, user_data))
        except redis.RedisError as e:
            logger.error(f"Error searching for users in the database: {e}")
        return matched_data
    
    def record_sync_details(self, guild_id, channel_id, count):
        """
        Records details of a sync operation to a guild channel.
        """
        try:
            self.redis.hset(f"sync_details:{guild_id}", mapping={
                "channel_id": channel_id,
                "count": count
            })
        except redis.RedisError as e:
            logger.error(f"Error recording sync details for guild {guild_id} in the database: {e}")
            
    def get_sync_details(self, guild_id):
        try:
            details = self.redis.hgetall(f"sync_details:{guild_id}")
            if details:
                return {k.decode('utf-8'): v.decode('utf-8') for k, v in details.items()}
            return {}
        except redis.RedisError as e:
            logger.error(f"Error getting sync details for guild {guild_id} from the database: {e}")
            return {}
    
    def set_last_sync_details(self, guild_id, sync_hash):
        """
        Records the last sync hash for a guild.
        """
        try:
            self.redis.hset("last_sync_hash", guild_id, sync_hash)
        except redis.RedisError as e:
            logger.error(f"Error setting last sync hash for guild {guild_id}: {e}")

    def get_last_sync_hash(self, guild_id):
        """
        Retrieves the last sync hash for a guild.
        """
        try:
            hash_bytes = self.redis.hget("last_sync_hash", guild_id)
            if hash_bytes is not None:
                return hash_bytes.decode('utf-8')
            return None
        except redis.RedisError as e:
            logger.error(f"Error getting last sync hash for guild {guild_id}: {e}")
            return None
        
    def list_all_sync_hashes(self):
        """
        Lists all guilds and their last sync hashes.
        """
        try:
            return {k.decode('utf-8'): v.decode('utf-8') for k, v in self.redis.hgetall("last_sync_hash").items()}
        except redis.RedisError as e:
            logger.error(f"Error listing all sync hashes from the database: {e}")
            return {}
        
    def list_all_sync_details(self):
        """
        Lists all guilds and their sync details.
        """
        try:
            return {k.decode('utf-8'): {k.decode('utf-8'): v.decode('utf-8') for k, v in v.items()} for k, v in self.redis.hgetall("sync_details").items()}
        except redis.RedisError as e:
            logger.error(f"Error listing all sync details from the database: {e}")
            return {}
        
    def check_if_guild_synced(self, guild_id, current_sync_hash):
        """
        Checks if a guild has already been synced with the current sync hash.
        """
        # Check if guild_id is in the database as an entry (sync_details:guild_id)
        if not self.redis.exists(f"sync_details:{guild_id}"):
            return False
        last_sync_hash = self.get_last_sync_hash(guild_id)
        return last_sync_hash == current_sync_hash

    def exists(self, user_id):
        """
        Checks if a user entry exists in the database.
        """
        try:
            return self.redis.exists(user_id)
        except redis.RedisError as e:
            logger.error(f"Error checking if user {user_id} exists in the database: {e}")
            return False

    def flush_db(self):
        """
        Clears the entire database, removing all keys and data.
        """
        try:
            self.redis.flushdb()
        except redis.RedisError as e:
            logger.error(f"Error flushing the database: {e}")


# db_0 = RedisDB(db=0)
# db_1 = RedisDB(db=1)
# db_2 = RedisDB(db=69)
# print(db_2.check_if_guild_synced('1213097209738960896', '99284ec6e103691c51ad89b101085ebdd9915e13efdef2a691886763d24a34ad'))
# print(f"All sync hashes: {db_2.list_all_sync_hashes()}")
# print(f"All sync details: {db_2.list_all_sync_details()}")
# db_0.flush_db()
# db_1.flush_db()
# db_2.flush_db()

# json_file_path = 'users.json'

# with open(json_file_path, 'r') as file:
#     users_data = json.load(file)

# for user_id, user_info in users_data.items():
#     db_0.set_user(
#         user_id,
#         user_info['username'],
#         user_info['reason'],
#         user_info['proof_link'],
#         user_info['folder_id']
#     )
    
# print(db_0.list_all_users_info())
# print(db_0.search_users('x'))