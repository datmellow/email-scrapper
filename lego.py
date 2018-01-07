import datetime
import re
from bs4 import BeautifulSoup
import html

global_remover = re.compile("(=(?<==)(.*?)(?=\s))", flags=re.DOTALL)


def parse_email(email):
    soup = BeautifulSoup(str(email), "lxml")
    if re.search("Order Confirmation", soup.text):
        email_date = email.get("date")
        try:

            order_date = datetime.datetime.strptime(email_date, "%d %b %Y %H:%M:%S %z").strftime("%m/%d/%Y")
        except Exception as e:
            order_date = datetime.datetime.strptime(email_date, "%a, %d %b %Y %H:%M:%S %z").strftime("%m/%d/%Y")
        order_number = None
        items = []
        cart = []
        prices = []
        quantites = []
        all_td_tags = soup.find_all("td")
        for index, data in enumerate(all_td_tags):
            text = re.sub("\t", "", html.unescape(data.text))
            if index in [1, 2, 3, 4]:
                continue
            if "Order Number" in text:
                first_search = re.search("(T.*)", text)
                order_number = first_search.group(0)
                break

        item_names = soup.find_all("td", attrs={"class": "3D=22padT15=22"})
        for item in item_names:
            name = re.sub(global_remover, "", item.text)
            name = re.sub("\n", "", name)
            name = " ".join([r.group(0) for r in re.finditer("(\d*?\w+)", name)])
            items.append(name)
            continue
        item_prices = soup.find_all("td", attrs={"class": "3D=22w50pc"})
        for price in item_prices:
            text = price.text
            if re.search("Qty", text):
                quantites.append(re.search(r"\d+", text).group(0))
                continue
            _ = re.sub("=2E", ".", text)
            _ = re.sub(global_remover, "", _)
            item_price = re.search("(\d+.\d+)", _)
            prices.append(float(item_price.group(0)))

        for item, quantity, price in zip(items, quantites, prices):
            try:
                unit_price = float(price) / float(quantity)
            except ZeroDivisionError:
                unit_price = float(price)
            cart.append((item, "${:,.2f}".format(price), quantity, "${:,.2f}".format(unit_price)))

        return {
            "date": order_date,
            "order_number": order_number,
            "items": cart,
            "discounts": "${:,.2f}".format(0)
        }
    return {}