import asyncio
import email
import imaplib
import openpyxl
import traceback
from collections import Counter

import ebgames
import lego
from amazon import get_data
from bestbuy import save_attachment
from config import *


class EmailReader:

    def __init__(self):
        self.mail = imaplib.IMAP4_SSL(host="imap.gmail.com", port=993)
        self.mail.login(username, password)
        self.stores = {}
        self.mail.select('inbox')
        self.workbook = openpyxl.Workbook()

    async def get_amazon(self):
        self.stores["amazonca"] = []
        emails_missed = 0
        self.mail.select('Shopping/Amazonca')
        result, data = self.mail.uid('search', None,
                                     "(FROM 'shipment-tracking@amazon.ca')")  # search and return uids instead
        for num in data[0].split():
            m, v = self.mail.uid("fetch", num, "(RFC822)")
            msg_body = email.message_from_bytes(v[0][1])
            # await add_new_item(await get_data(msg_body))
            try:
                email_data = await get_data(str(msg_body))
                self.stores['amazonca'].append(email_data)
            except Exception as e:
                print(e)
                print(traceback.format_tb(e.__traceback__))
                emails_missed += 1
                continue

    async def get_best_buy(self):
        self.stores["bestbuy"] = []
        self.mail.select('Shopping/BestBuy')
        result, data = self.mail.uid('search', None,
                                     "(FROM 'noreply@bestbuy.ca')")  # search and return uids instead
        for num in data[0].split():
            m, v = self.mail.uid("fetch", num, "(RFC822)")
            msg_body = email.message_from_bytes(v[0][1])
            try:
                if "Shipping" in msg_body.get("subject"):
                    email_data = save_attachment(msg_body)
                    if len(email_data) > 0:
                        self.stores['bestbuy'].append(email_data)
            except Exception as e:
                print(e)
                continue
        orders_cleaned = []
        new_orders = []
        for order in self.stores['bestbuy']:
            if order['order_number'] in orders_cleaned:
                continue
            cart = []
            total_quantity = Counter()
            total_prices = Counter()
            same_order = [o for o in self.stores['bestbuy'] if
                          o['order_number'] == order['order_number']]
            if len(same_order) == 1:
                formated_cart = []
                orders_cleaned.append(order['order_number'])
                for item in order['items']:
                    formated_cart.append(
                        (item[0], "${:,.2f}".format(item[1]), item[2], "${:,.2f}".format(item[3]))
                    )
                new_orders.append({
                    "date": order['date'],
                    "order_number": order['order_number'],
                    "items": formated_cart,
                    "discounts": "${:,.2f}".format(0)
                })
                continue
            for orde in same_order:
                for old_order in orde['items']:
                    total_quantity[old_order[0]] += old_order[2]
                    total_prices[old_order[0]] += old_order[1]
            for item, quantity in total_quantity.items():
                new_unit_price = total_prices[item] / quantity
                cart.append(
                    (item, "${:,.2f}".format(total_prices[item]), total_quantity[item],
                     "${:,.2f}".format(new_unit_price))
                )

            new_orders.append(
                {
                    "date": order['date'],
                    "order_number": order['order_number'],
                    "items": cart,
                    "discounts": "${:,.2f}".format(0)
                }
            )
            orders_cleaned.append(order['order_number'])
        self.stores['bestbuy'] = new_orders

    async def get_ebgames(self):
        self.stores["ebgames"] = []
        self.mail.select('Shopping/EBGames')
        result, data = self.mail.uid('search', None,
                                     "(FROM 'help@ebgames.ca')")  # search and return uids instead
        for num in data[0].split():
            m, v = self.mail.uid("fetch", num, "(RFC822)")
            msg_body = email.message_from_bytes(v[0][1])
            # await add_new_item(await get_data(msg_body))
            try:
                if "Shipment" in msg_body.get("subject"):
                    email_data = ebgames.parse_email(msg_body)
                    if len(email_data) > 0:
                        self.stores['ebgames'].append(email_data)
            except Exception as e:
                print(e)
                continue

    async def get_lego(self):
        self.stores["lego"] = []
        self.mail.select('Shopping/Lego')
        result, data = self.mail.uid('search', None,
                                     "(FROM 'legoshop@e.lego.com')")  # search and return uids instead
        for num in data[0].split():
            m, v = self.mail.uid("fetch", num, "(RFC822)")
            msg_body = email.message_from_bytes(v[0][1])
            # await add_new_item(await get_data(msg_body))
            try:
                email_data = lego.parse_email(msg_body)
                if len(email_data) > 0:
                    self.stores['lego'].append(email_data)
            except Exception as e:
                print(e)
                continue

    def finish(self):
        self.mail.logout()

    def save(self):
        self.workbook.guess_types = True
        default_sheet = self.workbook.get_sheet_by_name("Sheet")
        self.workbook.remove_sheet(default_sheet)
        for store in self.stores:
            sheet = self.workbook.create_sheet(title=store)
            for order in self.stores[store]:
                for item in order['items']:
                    row = [order['date'], order['order_number']]
                    row.extend(item)
                    row.append(order['discounts'])
                    try:
                        sheet.append(row)
                    except Exception as e:
                        print(e)
                        continue
        self.workbook.save("testbook.xlsx")
        print(f"Analyzed {sum([len(store) for store in self.stores.values()])} emails")

    async def gather_all(self):
        stores = [getattr(self, store) for store in dir(self) if
                  store.startswith("get_") and callable(getattr(self, store))]
        for store in stores:
            await store()


if __name__ == '__main__':
    reader = EmailReader()
    # asyncio.gather(reader.get_best_buy(), reader.get_amazon(), reader.get_ebgames())
    # asyncio.get_event_loop().run_until_complete(reader.get_best_buy())
    # asyncio.get_event_loop().run_until_complete(reader.get_amazon())
    # asyncio.get_event_loop().run_until_complete(reader.get_ebgames())
    # asyncio.get_event_loop().run_until_complete(reader.get_lego())
    asyncio.get_event_loop().run_until_complete(reader.gather_all())
    reader.save()
    reader.finish()