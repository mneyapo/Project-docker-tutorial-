#!/usr/bin/python

import MySQLdb
import pymysql
import unittest


def make_query(conn):
    cur = conn.cursor()

    query = ('SHOW DATABASES')

    cur.execute(query)

    for row in cur.fetchall():
        print(row[0])

    cur.close()
    conn.close()


class TestDatabaseConnection(unittest.TestCase):
    def test_pymysql(self):
        conn = pymysql.connect('localhost', 'root','root','mysql')
        make_query(conn)

    def test_mysqlconn(self):
        conn = MySQLdb.connect(
            host='localhost',
            user='root',
            passwd='root',
            db='mysql',
        )
        make_query(conn)


if __name__ == '__main__':
    unittest.main()
