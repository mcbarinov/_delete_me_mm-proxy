from bson import ObjectId
from mm_base1.db import BaseDB, DatabaseAny
from mm_mongo import MongoCollection

from app.models import Proxy, Source


class DB(BaseDB):
    def __init__(self, database: DatabaseAny) -> None:
        super().__init__(database)
        self.source: MongoCollection[str, Source] = MongoCollection(database, Source)
        self.proxy: MongoCollection[ObjectId, Proxy] = MongoCollection(database, Proxy)
