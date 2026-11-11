import sys

import numpy as np
import pandas as pd

from us_visa.configuration.mongo_db_connection import MongoDBClient
from us_visa.constants import DATABASE_NAME
from us_visa.exception import USvisaException


class USvisaData:
    """
    This class help to export entire mongo db record as pandas dataframe
    """

    def __init__(self):
        """ """
        try:
            self.mongo_client = MongoDBClient(database_name=DATABASE_NAME)
        except Exception as e:
            raise USvisaException(e, sys) from e

    def export_collection_as_dataframe(
        self, collection_name: str, database_name: str | None = None
    ) -> pd.DataFrame:
        try:
            """
            export entire collectin as dataframe:
            return pd.DataFrame of collection
            """
            client = self.mongo_client.client
            if client is None:  # pragma: no cover - set by MongoDBClient.__init__
                raise RuntimeError("MongoDB client is not initialised")

            collection = client[database_name or DATABASE_NAME][collection_name]

            df = pd.DataFrame(list(collection.find()))
            if "_id" in df.columns.to_list():
                df = df.drop(columns=["_id"], axis=1)
            df.replace({"na": np.nan}, inplace=True)
            return df
        except Exception as e:
            raise USvisaException(e, sys) from e
