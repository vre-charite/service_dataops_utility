import shutil
import unittest
import time
import pytest
import asyncio

from unittest import result
from tests.logger import Logger
from tests.prepare_test import SetUpTest
import os
from config import ConfigClass


class TestAPIFileLock(unittest.TestCase):
    log = Logger(name='test_api_file_lock.log')
    test = SetUpTest(log)

    @classmethod
    def setUpClass(cls):
        cls.log = cls.test.log
        cls.app = cls.test.app

    @classmethod
    def tearDownClass(cls):
        pass

    def test_01_read_lock(self):

        payload = {
            "resource_key": "test_01_read_lock",
            "operation": "read"
        }
        
        try:
            response = self.app.post(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 200)

            time.sleep(2)

            # now assume the read operation is finish, try to unlock it
            response = self.app.delete(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 200)

        except Exception as e:
            self.log.error(e)
            raise e


    def test_02_read_lock_not_exist(self):
        payload = {
            "resource_key": "test_02_read_lock_not_exist",
            "operation": "read"
        }
        
        try:
            # if we try to unlock the non_exist lock, api return 404
            response = self.app.delete(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 400)

        except Exception as e:
            self.log.error(e)
            raise e

    def test_03_read_lock_not_exist(self):

        # function to do the read lock + unlock
        async def read_operation_setup():
            response = self.app.post(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 200)

        async def add_read_op(num=10):
            for _ in range(num):
                read_operation_setup()


        async def read_operation_finish():
            # now assume the read operation is finish, try to unlock it
            response = self.app.delete(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 200)

        async def remove_read_op(num=10):
            for _ in range(num):
                read_operation_finish()

            
        payload = {
            "resource_key": "test_03_read_lock_not_exist",
            "operation": "read"
        }
        
        try:
            event_loop = asyncio.get_event_loop_policy().new_event_loop()
            event_loop.run_until_complete(add_read_op())

            print("====== wait few seconds to setup")
            time.sleep(4)

            event_loop.run_until_complete(remove_read_op())

            print("====== wait few seconds to finish")
            time.sleep(1)

            response = self.app.get(f"/v2/resource/lock/", params=payload)
            result = response.json().get("result")
            print(result)
            self.assertEqual(result.get("status"), None)

            event_loop.close()

        except Exception as e:
            self.log.error(e)
            raise e




    ############################################ write lock ############################################
    def test_11_write_lock(self):

        payload = {
            "resource_key": "test_11_write_lock",
            "operation": "write"
        }
        
        try:
            response = self.app.post(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 200)

            time.sleep(2)

            # now assume the read operation is finish, try to unlock it
            response = self.app.delete(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 200)

        except Exception as e:
            self.log.error(e)
            raise e


    def test_12_write_lock_not_exist(self):
        payload = {
            "resource_key": "test_12_write_lock_not_exist",
            "operation": "write"
        }
        
        try:

            # if we try to unlock the non_exist lock, api return 404
            response = self.app.delete(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 400)

        except Exception as e:
            self.log.error(e)
            raise e

    def test_13_read_lock_not_exist(self):

        # function to do the read lock + unlock
        async def write_operation_setup():
            response = self.app.post(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 200)

        async def add_write_op(num=10):
            for _ in range(num):
                write_operation_setup()


        async def write_operation_finish():
            # now assume the read operation is finish, try to unlock it
            response = self.app.delete(f"/v2/resource/lock/", json=payload)
            self.assertEqual(response.status_code, 200)

        async def remove_write_op(num=10):
            for _ in range(num):
                write_operation_finish()

            
        payload = {
            "resource_key": "test_03_read_lock_not_exist",
            "operation": "write"
        }
        
        try:
            event_loop = asyncio.get_event_loop_policy().new_event_loop()
            event_loop.run_until_complete(add_write_op())

            print("====== wait few seconds to setup")
            time.sleep(4)

            event_loop.run_until_complete(remove_write_op())

            print("====== wait few seconds to finish")
            time.sleep(1)

            response = self.app.get(f"/v2/resource/lock/", params=payload)
            result = response.json().get("result")
            print(result)
            self.assertEqual(result.get("status"), None)

            event_loop.close()

        except Exception as e:
            self.log.error(e)
            raise e
