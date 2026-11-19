"""Testes de isolamento e consentimento de comunicados V450 (SQLite descartável)."""
import sqlite3
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

import nowup_customer_comms450 as comm


class Alerts:
    def __init__(self):
        self.items = []

    def enqueue(self, conn, uid, event_id, payload):
        self.items.append((uid, event_id, payload))


class CommunicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / "test.sqlite3")

        def connect():
            c = sqlite3.connect(self.path)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA foreign_keys=ON")
            return c

        self.connect = connect
        with self.connect() as c:
            c.executescript("""
                CREATE TABLE professionals (
                    id INTEGER PRIMARY KEY, slug TEXT, blocked INTEGER,
                    admission_status TEXT, plan_active TEXT);
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY, role TEXT, customer_store345 INTEGER,
                    is_active INTEGER, email_verified INTEGER);
                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                    title TEXT, message TEXT, link TEXT, created_at TEXT);
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY, professional_id INTEGER, name TEXT,
                    image_filename TEXT, price_cents INTEGER, promo_price_cents INTEGER, available INTEGER);
                INSERT INTO professionals VALUES (1,'sede-zero',0,'approved','cardapio');
                INSERT INTO professionals VALUES (2,'outra-loja',0,'approved','cardapio');
                INSERT INTO users VALUES (10,'customer',1,1,1);
                INSERT INTO users VALUES (11,'customer',2,1,1);
                INSERT INTO users VALUES (12,'customer',1,1,0);
                INSERT INTO products VALUES (4,1,'Combo Sede','',4500,3990,1);
                INSERT INTO products VALUES (5,2,'Combo outra','',7000,0,1);
            """)
        self.alerts = Alerts()
        comm.G = {"db":self.connect,"nowup_alerts112":self.alerts}
        comm.setup()

    def test_external_links_must_use_https(self):
        self.assertEqual(comm.safe_link("https://example.com/loja"),"https://example.com/loja")
        from fastapi import HTTPException
        for link in ["javascript:alert(1)","http://example.com","https://u:p@example.com"]:
            with self.assertRaises(HTTPException):
                comm.safe_link(link)

    def test_products_are_tenant_scoped(self):
        with self.connect() as c:
            selected = comm.visible_products(c,{"id":1},[4,5])
            self.assertEqual([x["id"] for x in selected],[4])

    def test_only_opted_in_verified_customers_of_merchant_are_notified(self):
        with self.connect() as c:
            c.execute("INSERT INTO merchant_comms450_consent VALUES(10,1,1,'v450','2026-11-19')")
            c.execute("INSERT INTO merchant_comms450_consent VALUES(11,2,1,'v450','2026-11-19')")
            c.execute("INSERT INTO merchant_comms450_consent VALUES(12,1,1,'v450','2026-11-19')")
            due=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
            c.execute("""INSERT INTO merchant_comms450
              (professional_id,kind,title,body,product_ids,created_at,scheduled_at)
              VALUES(1,'promocao','Combo novo','Conheça nosso combo','[4]',?,?)""",(due,due))
        comm.worker_once()
        with self.connect() as c:
            notices=c.execute("SELECT user_id,link FROM notifications ORDER BY id").fetchall()
            row=c.execute("SELECT state,recipients,sent FROM merchant_comms450").fetchone()
        self.assertEqual([x["user_id"] for x in notices],[10])
        self.assertEqual(notices[0]["link"],"/p/sede-zero/comunicados/1")
        self.assertEqual((row["state"],row["recipients"],row["sent"]),("sent",1,1))
        self.assertEqual(len(self.alerts.items),1)

    def test_opt_out_before_due_prevents_delivery(self):
        with self.connect() as c:
            c.execute("INSERT INTO merchant_comms450_consent VALUES(10,1,0,'v450','2026-11-19')")
            due=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
            c.execute("""INSERT INTO merchant_comms450
              (professional_id,kind,title,body,created_at,scheduled_at)
              VALUES(1,'aviso','Aviso','Entrega lenta',?,?)""",(due,due))
        comm.worker_once()
        with self.connect() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM notifications").fetchone()[0],0)
        self.assertFalse(self.alerts.items)


    def test_push_optout_drops_previously_queued_notification(self):
        from unittest.mock import patch
        import nowup_alerts112 as alerts
        with self.connect() as db:
            db.execute("INSERT INTO merchant_comms450_consent VALUES(10,1,0,'v450','2026-11-19')")
            db.execute("""INSERT INTO merchant_comms450
                (professional_id,kind,title,body,created_at,scheduled_at,state)
                VALUES(1,'promocao','Oferta','Promoção',?,?, 'sent')""",
                (comm.now(),comm.now()))
        alerts.configure(self.connect, lambda *args: None)
        alerts.initialize()
        with self.connect() as db:
            alerts.enqueue(db,10,101,{'title':'Oferta','body':'Promoção','tag':'nowup-com450-1'})
        with patch.object(alerts.push,'send',return_value=True) as sender:
            self.assertTrue(alerts.process())
            sender.assert_not_called()
        with self.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM customer_push112').fetchone()[0],0)

    def test_push_uses_only_this_store_device(self):
        from unittest.mock import patch
        import nowup_alerts112 as alerts
        with self.connect() as db:
            db.execute("""CREATE TABLE push_subscriptions(
               endpoint TEXT PRIMARY KEY,user_id INTEGER,session_hash TEXT,subscription TEXT)""")
            db.execute("INSERT INTO push_subscriptions VALUES('device-store',10,'s','{}')")
            db.execute("INSERT INTO push_subscriptions VALUES('device-other',10,'s','{}')")
            db.execute("INSERT INTO merchant_comms450_devices VALUES(10,1,'device-store','2026-11-19')")
            db.execute("INSERT INTO merchant_comms450_consent VALUES(10,1,1,'v450','2026-11-19')")
            db.execute("""INSERT INTO merchant_comms450
                (professional_id,kind,title,body,created_at,scheduled_at,state)
                VALUES(1,'promocao','Oferta','Promoção',?,?, 'sent')""",
                (comm.now(),comm.now()))
        alerts.configure(self.connect, lambda *args: None)
        alerts.initialize()
        with self.connect() as db:
            alerts.enqueue(db,10,102,{'title':'Oferta','body':'Promoção','tag':'nowup-com450-1'})
        with patch.object(alerts.push,'send',return_value=True) as sender:
            self.assertTrue(alerts.process())
            self.assertEqual(sender.call_count,1)
            self.assertEqual(sender.call_args.args[0]['endpoint'],'device-store')


if __name__ == "__main__":
    unittest.main()
