# import psycopg2
from elasticsearch import Elasticsearch
import os,re,ast
import random
import pandas as pd
import time
from ChatBot_Extract_Intent.config_app.config import get_config
from ChatBot_Extract_Intent.module.few_shot_sentence import find_closest_match
# from langchain_groq import ChatGroq
# llm = ChatGroq(model="llama3-70b-8192",api_key= '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')
ELASTIC_HOST = "http://10.248.243.105:9200"
config_app = get_config()
data_private = config_app['parameter']['data_private']
number_size_elas = config_app['parameter']['num_size_elas']
df = pd.read_excel(data_private)
# ELASTIC_CLOUD_ID= "My_deployment:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJDNhMTAxYThmYmRjNjQ1MDk4ZGIwMmM2ZDU1ZWU2MjU3JGYxMzhjMzZmMDI5YjRiZTc5NzhkZjUwNzhjZjZlMmU0"
# ELASTIC_API_KEY= "Uk82aktwQUJLeFdtc05QTDlhRVQ6YXRGMjJ4ZFVTQm12NEp1UzU5SVNrZw=="

def init_elastic(df, index_name,hosts):
    # Create the client instance
    client = Elasticsearch(hosts=[hosts])

    # Define the mappings
    mappings = {
        "properties": {
            "LINK_SP": {"type" : "text"},
            "PRODUCT_INFO_ID": {"type": "text"},
            "GROUP_PRODUCT_NAME": {"type": "keyword"},
            "PRODUCT_NAME" : {"type": "text"},
            "SPECIFICATION_BACKUP": {"type": "text"},
            "POWER": {"type": "float"},
            "WEIGHT": {"type": "float"},
            "VOLUME": {"type": "float"},
            "RAW_PRICE": {"type": "integer"}
        }
    }

    # Create the index with mappings
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body={"mappings": mappings})
        # Index documents
        for i, row in df.iterrows():
            doc = {
                "LINK_SP": row["LINK_SP"],
                "PRODUCT_INFO_ID": row["PRODUCT_INFO_ID"],
                "GROUP_PRODUCT_NAME": row["GROUP_PRODUCT_NAME"],
                "PRODUCT_NAME": row["PRODUCT_NAME"],
                "SPECIFICATION_BACKUP": row["SPECIFICATION_BACKUP"],
                "POWER": row["POWER"],
                "WEIGHT": row["WEIGHT"],
                "VOLUME": row["VOLUME"],
                "RAW_PRICE": row["RAW_PRICE"]
            }
            client.index(index=index_name, id=i, document=doc)

        client.indices.refresh(index=index_name)
        print(f"Index {index_name} created.")
    else:
        print(f"Index {index_name} already exists.")

    return client

def parse_price_range(value):
    pattern = r"(?P<prefix>\b(dưới|trên|từ|đến|khoảng)\s*)?(?P<number>\d+(?:,\d+)*)\s*(?P<unit>triệu|nghìn|tr|k|kg|l|lít|W|w|t)?\b"

    min_price = 0
    max_price = 100000000
    for match in re.finditer(pattern, value, re.IGNORECASE):
        prefix = match.group('prefix') or ''
        number = float(match.group('number').replace(',', ''))
        unit = match.group('unit') or ''

        if unit.lower() in ['triệu','tr','t']:
            number *= 1000000
        elif unit.lower() in ['nghìn','k']:
            number *= 1000

        if prefix.lower().strip() == 'dưới':
            max_price = min(max_price, number)
        elif prefix.lower().strip() == 'trên':
            min_price = min(max_price, number)
        elif prefix.lower().strip() == 'từ':
            min_price = min(max_price, number)
        elif prefix.lower().strip() == 'đến':
            max_price = max(min_price, number)
        else:  # Trường hợp không có từ khóa
            min_price = number * 0.5
            max_price = number * 1.5
    if min_price == float('inf'):
        min_price = 0
    print('min_price, max_price:',min_price, max_price)
    return min_price, max_price

def search_intent(client, index_name, product_name, product, intent, value, power, weight, volume):
    print("check_product_ok_intent", product_name)
    print("check intent", intent)
    order = "asc"  # Default order
    cheap_keywords = ["rẻ", "giá rẻ", "giá thấp", "bình dân", "tiết kiệm", "khuyến mãi", "giảm giá", "hạ giá", "giá cả phải chăng", "ưu đãi"]
    expensive_keywords = ["giá đắt", "giá cao", "xa xỉ", "sang trọng", "cao cấp", "đắt đỏ", "chất lượng cao", "hàng hiệu", "hàng cao cấp", "thượng hạng"]
    quantity_intent = ['số lượng','bao nhiêu','mấy loại']
    word = ""
    for keyword in cheap_keywords:
        if keyword == value.lower():
            order = "asc"
            word = keyword
            value = ""
    for keyword in expensive_keywords:
        if keyword == value.lower():
            order = "desc"
            word = keyword
            value = ""
    # Build the base query
    # Create the Elasticsearch query if a product is found
    # if inten == ''di
    if intent == 'so sánh':
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "GROUP_PRODUCT_NAME": product
                            }
                        }
                    ],
                    "should": [
                        {
                            "match": {
                                "PRODUCT_NAME": product_name
                            }
                        }
                    ]
                }
                },
            "size": number_size_elas,
            }
    else:
    # Create the Elasticsearch query if a product is found
        query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "GROUP_PRODUCT_NAME": product
                                }
                            },
                            {
                                "match": {
                                    "SPECIFICATION_BACKUP": intent
                                }
                            }
                        ],
                        "should": [
                            {
                                "match": {
                                    "PRODUCT_NAME": product_name
                                }
                            }
                        ]
                    }
                    },
                "size": number_size_elas,
            }

    if word:
        print("check intent value in", word)
        query["sort"] = [
            {"RAW_PRICE": {"order": order}}
        ]

    if value :
      print("check value", value)
      min_price, max_price = parse_price_range(value)
      price_filter = {
          "range": {
              "RAW_PRICE": {
                  "gte": min_price,
                  "lte": max_price
              }
          }
      }
      query["query"]["bool"]["must"].append(price_filter)

    if power:
      min_power, max_power = parse_price_range(power)
      power_filter = {
          "range": {
              "POWER": {
                  "gte": min_power,
                  "lte": max_power
              }
          }
      }
      query["query"]["bool"]["must"].append(power_filter)

    if weight:
        min_weight, max_weight = parse_price_range(weight)
        weight_filter = {
            "range": {
                "WEIGHT": {
                    "gte": min_weight,
                    "lte": max_weight
                }
            }
        }
        query["query"]["bool"]["must"].append(weight_filter)

    if volume:
        min_volume, max_volume = parse_price_range(volume)
        volume_filter = {
            "range": {
                "VOLUME": {
                    "gte": min_volume,
                    "lte": max_volume
                }
            }
        }
        query["query"]["bool"]["must"].append(volume_filter)
    # Execute the search query
    print('check query', query)
    response = client.search(index=index_name, body=query)
    return response
        
def search_values(client, index_name, product_name, product, value, power, weight, volume):
    print("check_search_values", value)
    order = "asc"  # Default order
    cheap_keywords = ["rẻ", "giá rẻ", "giá thấp", "bình dân", "tiết kiệm", "khuyến mãi", "giảm giá", "hạ giá", "giá trung", "ưu đãi","rẻ hơn"]
    expensive_keywords = ["giá đắt", "giá cao", "xa xỉ", "sang trọng", "cao cấp", "đắt đỏ", "chất lượng cao", "hàng hiệu", "hàng cao cấp", "thượng hạng"]
    intent_value = cheap_keywords + expensive_keywords
    word = ""
    for keyword in cheap_keywords:
        if keyword == value.lower():
            order = "asc"
            word = keyword
            value = ""
    for keyword in expensive_keywords:
        if keyword == value.lower():
            order = "desc"
            word = keyword
            value = ""
    # Build the base query
    # Create the Elasticsearch query if a product is found
    print("check intent value out", word)
    if product:
      query = {
          "query": {
              "bool": {
                  "must": [
                      {
                          "match": {
                              "GROUP_PRODUCT_NAME": product
                          }
                      },
                      {
                          "match": {
                              "PRODUCT_NAME": product_name
                          }
                      }
                  ]
              }
          },
          "size": number_size_elas
      }

    if word:
        print("check intent value in", word)
        query["sort"] = [
            {"RAW_PRICE": {"order": order}}
        ]

    # Add intent-based filters
    if value:
        min_price, max_price = parse_price_range(value)
        price_filter = {
            "range": {
                "RAW_PRICE": {
                    "gte": min_price,
                    "lte": max_price
                }
            }
        }
        query["query"]["bool"]["must"].append(price_filter)

    if power:
        min_power, max_power = parse_price_range(power)
        power_filter = {
            "range": {
                "POWER": {
                    "gte": min_power,
                    "lte": max_power
                }
            }
        }
        query["query"]["bool"]["must"].append(power_filter)

    if weight:
        min_weight, max_weight = parse_price_range(weight)
        weight_filter = {
            "range": {
                "WEIGHT": {
                    "gte": min_weight,
                    "lte": max_weight
                }
            }
        }
        query["query"]["bool"]["must"].append(weight_filter)

    if volume:
        print("check volume", volume)
        min_volume, max_volume = parse_price_range(volume)
        volume_filter = {
            "range": {
                "VOLUME": {
                    "gte": min_volume,
                    "lte": max_volume
                }
            }
        }
        query["query"]["bool"]["must"].append(volume_filter)


    res = client.search(index=index_name, body=query)
    print(res)

    return res

def search_product(client, index_name, product_name,product):
    print("check_search_product_ok2", product_name)

    query = {
        "query": {
            "bool": {
                "must":
                    {
                        "match": {
                            "GROUP_PRODUCT_NAME": product
                        }
                    }
                ,
                "should":  {
                      "match": {
                          "PRODUCT_NAME": product_name
                      }
                  }
            }
        },
        "size" : number_size_elas
    }
    res = client.search(index=index_name, body=query)
    print(query)
    return res

def search_quantity(client, index_name, product_name,product):
    query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "GROUP_PRODUCT_NAME": product
                            }
                        }
                    ],
                    "should": [
                        {
                            "match": {
                                "PRODUCT_NAME": product_name
                            }
                        }
                    ]
                }
                },
            "size": 100,
            }
    res = client.search(index=index_name, body=query)
    print(query)
    return res

def search_db(demands):
    #init 
    list_product = df['GROUP_PRODUCT_NAME'].unique()
    index_name = "product5"
    client = init_elastic(df,index_name, ELASTIC_HOST)
    print("====== Check few short ========", demands)
    product_names = []
    # if isinstance(demands['object'], str):
    #     product_names = [demands['object']]
    # if isinstance(demands, dict):
    #     product_names = demands['object']
    if len(demands)>1:
        product_names = demands['object']
        if isinstance(demands['value'], list):
            values = demands['value']
        else:
            values = ast.literal_eval(demands['value'])
        power = demands['power']
        weight = demands['weight']
        volume = demands['volume']
        intent = demands['intent']
    else:
        product_names = demands['object']
        values = ['']*len(demands['object'])
        power = ''
        weight = ''
        volume = ''
        intent = ''
    print("check values", values)
    result = []
    t1 = time.time()
    ok = 0
    out_text = ""
    quantity_intent = ['số lượng','bao nhiêu','mấy loại','số lượng sản phẩm']
    print('check product names', product_names)
    for product_name, value in zip(product_names, values):
    # for product_name in product_names:
        print("check demands", product_name)
        product = find_closest_match(product_name, list_product)
        # out_text += f"\nchúng tôi bán sản phẩm {product_name} KHÔNG BÁN CÁC SẢN PHẨM KHÁC:\n"
        print('check product match', product)
        if product:
            if intent and (value or power or weight or volume) or intent:
                if intent in quantity_intent:
                    resp = search_quantity(client, index_name, product_name,product)
                    ok = 1
                else:
                    resp = search_intent(client, index_name, product_name,product, intent, value, power, weight, volume)
                    ok = 2
            elif value or power or weight or volume:
                resp = search_values(client, index_name, product_name,product, value, power, weight, volume)
                ok = 3
            else:
                resp = search_product(client, index_name, product_name, product)
                ok = 3
            result.append(resp) 
    # print("check result", result)
    print("check ok", ok)
    # result
    products = []
    product_dict = {}
    s_name = ''
    for product_name, product in zip(product_names, result):
        s_name = product_name
        # Check query is None
        if product['hits']['hits'] == [] and ok != 0:
            out_text += f"Bên mình không có thông tin mà bạn yêu cầu. Có phải bạn tìm kiếm sản phẩm {product_name}. Tôi có một số đề xuất mới cho bạn"
            break
        out_text += f"Chúng tôi có kinh doanh sản phẩm {product_name} mà bạn quan tâm. KHÔNG BÁN SẢN PHẨM KHÁC:\n"
        cnt = 0
        for i, hit in enumerate(product['hits']['hits']):
            cnt +=1
            check_score = hit.get('_score')
            product_details = hit['_source']
            print(check_score)
            product =  {
                "code" : "",
                "name" : "",
                "link" : ""
            }
            if check_score is None or float(check_score) >= 3:
                if ok == 3 and i < 5 or check_score is None:
                    out_text += f"  {i + 1}. {product_details['PRODUCT_NAME']}\n"
                    out_text += f"  Giá tiền: {product_details['RAW_PRICE']} VND\n"
                    out_text += f"  Thông số kỹ thuật: {product_details['SPECIFICATION_BACKUP']}\n"
                    product = {
                        "code": product_details['PRODUCT_INFO_ID'],
                        "name": product_details['PRODUCT_NAME'],
                        "link": product_details['LINK_SP']
                    }
                    product_dict[f'{i+1}'] = product_details['PRODUCT_NAME']
                    # print("out_text ok2")
                elif ok == 2:
                    if len(product_names) > 1 and i < 1:
                        out_text += f"\n{i + 1}. {product_details['PRODUCT_NAME']}\n"

                        out_text += f"  Thông số kỹ thuật: {product_details['SPECIFICATION_BACKUP']}\n"
                        product = {
                            "code": product_details['PRODUCT_INFO_ID'],
                            "name": product_details['PRODUCT_NAME'],
                            "link": product_details['LINK_SP']
                        }
                    elif len(product_names) == 1 and i < 2:
                        out_text += f"\n{i + 1}. {product_details['PRODUCT_NAME']}\n"

                        out_text += f"  Thông số kỹ thuật: {product_details['SPECIFICATION_BACKUP']}\n"
                        product = {
                            "code": product_details['PRODUCT_INFO_ID'],
                            "name": product_details['PRODUCT_NAME'],
                            "link": product_details['LINK_SP']
                        }
                if len(products) < 10 and product['code'] != "":
                    products.append(product)
        if ok == 1:
            out_text += f"Bên tôi đang có {cnt} sản phẩm {s_name}. Bạn quan tâm chi tiết đến sản phẩm nào"

    if ok==0:
        out_text += f"Bạn có thể cho tôi biết thêm thông tin chi tiết sản phẩm bạn quan tâm để tôi có thể hỗ trợ bạn được không?" 
    print("time elastic search",time.time() - t1)
    print('======== elasticsearch output ==========', out_text)
    return product_dict, out_text, products