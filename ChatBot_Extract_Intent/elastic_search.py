# import psycopg2
from elasticsearch import Elasticsearch
import os,re,ast
import pandas as pd
import time
from config_app.config import get_config
from ChatBot_Extract_Intent.module.few_shot_sentence import find_closest_match

config_app = get_config()

ELASTIC_HOST = config_app['parameter']['elastic_url']
number_size_elas = config_app['parameter']['num_size_elas']

df = pd.read_excel(config_app['parameter']['data_private'])

def init_elastic(df, index_name,hosts):
    # Create the client instance
    client = Elasticsearch(hosts=[hosts])

    # Define the mappings
    mappings = {
        "properties": {
            "product_info_id": {"type": "text"},
            "group_product_name":{"type": "keyword"},
            "product_code":{ "type":"text"},
            "group_name": {"type": "text"},
            "product_name": {"type": "text"},
            "file_path": {"type" : "text"},
            "short_description": {"type": "text"},
            "specification": {"type": "text"},
            "power": {"type": "float"},
            "weight": {"type": "float"},
            "volume": {"type": "float"},
            "lifecare_price": {"type": "float"}
        }
    }

    # Create the index with mappings
    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body={"mappings": mappings})
        # Index documents
        for i, row in df.iterrows():
            doc = {
                "product_info_id": row["product_info_id"],
                "group_product_name": row["group_product_name"],
                "product_code": row["product_code"],
                "group_name": row["group_name"],
                "product_name": row["product_name"],
                "file_path": row["file_path"],
                "short_description": row["short_description"],
                "specification": row["specification"],
                "power": row["power"],
                "weight": row["weight"],
                "volume": row["volume"],
                "lifecare_price": row["lifecare_price"]
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
            min_price = number * 0.75
            max_price = number * 1.25
    if min_price == float('inf'):
        min_price = 0
    return min_price, max_price

def search_intent(client, index_name, product_name, intent, value, power, weight, volume):
    order = "asc"  # Default order
    cheap_keywords = ["rẻ", "giá rẻ", "giá thấp", "bình dân", "tiết kiệm", "khuyến mãi", "giảm giá", "hạ giá", "giá cả phải chăng", "ưu đãi"]
    expensive_keywords = ["cao","giá đắt", "giá cao", "xa xỉ", "sang trọng", "cao cấp", "đắt đỏ", "chất lượng cao", "hàng hiệu", "hàng cao cấp", "thượng hạng"]
    word = ""
    for keyword in cheap_keywords:
        if keyword in value.lower():
            order = "asc"
            word = keyword
            value = ""
    for keyword in expensive_keywords:
        if keyword in value.lower():
            order = "desc"
            word = keyword
            value = ""
    
    # Create the Elasticsearch query if a product is found
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "specification": intent
                        }
                    },
                    {
                        "match": {
                            "group_name": product_name
                        }
                    }
                ]
            }
            },
        "size": 5,
    }

    if word:
        query["sort"] = [
            {"lifecare_price": {"order": order}}
        ]

    if value :
      min_price, max_price = parse_price_range(value)
      price_filter = {
          "range": {
              "lifecare_price": {
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
              "power": {
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
                "weight": {
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
                "volume": {
                    "gte": min_volume,
                    "lte": max_volume
                }
            }
        }
        query["query"]["bool"]["must"].append(volume_filter)
    # Execute the search query
    response = client.search(index=index_name, body=query)
    return response
       
def search_values(client, index_name, product, product_name, value, power, weight, volume):
    order = "asc"  # Default order
    cheap_keywords = ["rẻ", "giá rẻ", "giá thấp", "bình dân", "tiết kiệm", "khuyến mãi", "giảm giá", "hạ giá", "giá cả phải chăng", "ưu đãi"]
    expensive_keywords = ["giá đắt", "giá cao", "xa xỉ", "sang trọng", "cao cấp", "đắt đỏ", "chất lượng cao", "hàng hiệu", "hàng cao cấp", "thượng hạng"]
    word = ""
    for keyword in cheap_keywords:
        if keyword in value.lower():
            order = "asc"
            word = keyword
            value = ""
    for keyword in expensive_keywords:
        if keyword in value.lower():
            order = "desc"
            word = keyword
            value = ""
    # Build the base query
    # Create the Elasticsearch query if a product is found
    
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "match": {
                            "group_name": product_name
                        }
                    },
                    {
                        "match": {
                            "group_product_name": product
                        }
                    }
                ]
            }
        },
        "size": 5
    }

    if word:
        query["sort"] = [
            {"lifecare_price": {"order": order}}
        ]

    # Add intent-based filters
    if value:
        min_price, max_price = parse_price_range(value)
        price_filter = {
            "range": {
                "lifecare_price": {
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
                "power": {
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
                "weight": {
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
                "volume": {
                    "gte": min_volume,
                    "lte": max_volume
                }
            }
        }
        query["query"]["bool"]["must"].append(volume_filter)


    res = client.search(index=index_name, body=query)

    return res

def search_quantity(client, index_name, product, product_name, value, power, weight, volume):
    query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "group_product_name": product
                            }
                        },
                        {
                            "match": {
                                "group_name": product_name
                            }
                        }
                    ]
                }
                },
            "size": 100,
            }
    if value:
        min_price, max_price = parse_price_range(value)
        price_filter = {
            "range": {
                "lifecare_price": {
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
                "power": {
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
                "weight": {
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
                "volume": {
                    "gte": min_volume,
                    "lte": max_volume
                }
            }
        }
        query["query"]["bool"]["must"].append(volume_filter)
    res = client.search(index=index_name, body=query)
    return res

def search_compare(client, index_name, product, product_name, value, power, weight, volume):
    query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "product_name": product_name
                            }
                        }
                    ]
                }
                },
            "size": 1,
          }
    if value :
        print("check value", value)
        min_price, max_price = parse_price_range(value)
        price_filter = {
            "range": {
                "lifecare_price": {
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
              "power": {
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
                "weight": {
                    "gte": min_weight,
                    "lte": max_weight
                }
            }
        }
        query["query"]["bool"]["must"].append(weight_filter)

    if volume:
        min_volume, max_volume = parse_price_range(volume)
        print(min_volume, max_volume)
        volume_filter = {
            "range": {
                "volume": {
                    "gte": min_volume,
                    "lte": max_volume
                }
            }
        }
        query["query"]["bool"]["must"].append(volume_filter)

    res = client.search(index=index_name, body=query)
    return res

def search_product(client, index_name, product_name):
    query = {
        "query": {
            "bool": {
                "must": [
                    
                    {
                        "match": {
                            "product_name": product_name
                        }
                    }
                ]
            }
        }
    }


    res = client.search(index=index_name, body=query)
    return res

def search_db(demands):
    #init 
    out_text = ""
    products = []
    product_dict = {}
    s_name = ''
    index_name = "test12"
    client = init_elastic(df,index_name, ELASTIC_HOST)
    product_names = []
    list_product = df['group_name'].unique()
    check_match_product = find_closest_match(demands['object'][0], list_product)
    if check_match_product[1] < 65:
        out_text += f"Anh/chị có thể cho tôi biết thêm thông tin chi tiết sản phẩm  Anh/chị quan tâm để tôi có thể hỗ trợ Anh/chị được không?" 
        ok = 0
        print(check_match_product)
        return product_dict, out_text, products, ok
    elif len(demands)>1:
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

    result = []
    t1 = time.time()
    compare_intent = ['so sánh', 'hơn']
    quantity_intent = ['số lượng','bao nhiêu','mấy loại','số lượng sản phẩm', 'danh sách', 'tổng số','mấy','liệt kê số lượng','liệt kê']
    print('------check objects-----:', product_names)
    for product_name, value in zip(product_names, values):
        print("check demands", product_name)
        product_match = find_closest_match(product_name, list_product)[0]
        result_df = df[df['group_name'] == product_match]
        product = result_df['group_product_name'].tolist()[0]
        # full option intent, giá, công suất, khối lượng, dung tích
        if intent and (value or power or weight or volume) or intent:
            # Count quantity each group name
            if intent in quantity_intent:
                resp = search_quantity(client, index_name, product, product_name, value, power, weight, volume)
                ok = 1 # count
            elif intent in compare_intent:
                resp = search_compare(client, index_name, product_name, value, power, weight, volume)
                ok = 2 
            else:
                resp = search_intent(client, index_name, product_name, intent, value, power, weight, volume)
                ok = 2 
        elif value or power or weight or volume:
            resp = search_values(client, index_name, product, product_name,value,  power, weight, volume)
            ok = 2 
        else:
            resp = search_product(client, index_name, product_name)
            ok = 2

        result.append(resp)

    print("check ok", ok)
    # print("result", result)
    for product_name, product in zip(product_names, result):
        s_name = product_name
        # Check query is None
        if product['hits']['hits'] == [] and ok != 0:
            out_text += f"Hiện tại tôi không tìm thấy thông tin {product_name} mà anh/chị cần. Tôi có một số đề xuất mới cho Anh/chị"
            break
        cnt = 0
        quantity_name = ""
        for i, hit in enumerate(product['hits']['hits']):
            check_score = hit.get('_score')
            product_details = hit['_source']
            product =  {
                "code" : "",
                "name" : "",
                "link" : ""
            }
            if check_score is None or float(check_score) >= 2.5:
                cnt+=1
                if ok == 2:
                    if len(product_names) > 1 and i < 2:
                        out_text += f"\n{i + 1}. {product_details['product_name']} - Mã: {product_details['product_code']}"
                        out_text +=  " - Giá tiền: {:,.0f} đ\n".format(product_details['lifecare_price'])
                        # out_text += f"  Mã kho: {product_details['product_code']}\n"
                        out_text += f"  Thông số kỹ thuật: {product_details['specification']}\n"
                        product = {
                            "code": product_details['product_info_id'],
                            "name": product_details['product_name'],
                            "link": product_details['file_path']
                        }
                    elif len(product_names) == 1 and i < 4:
                        out_text += f"\n{i + 1}. {product_details['product_name']} - Mã: {product_details['product_code']}"
                        out_text +=  " - Giá tiền: {:,.0f} đ\n".format(product_details['lifecare_price'])
                        # out_text += f"  Mã kho: {product_details['product_code']}\n"
                        out_text += f"  Thông số kỹ thuật: {product_details['specification']}\n"
                        product = {
                            "code": product_details['product_info_id'],
                            "name": product_details['product_name'],
                            "link": product_details['file_path']
                        }
                        product_dict[f'{i+1}'] = product_details['product_name']
                elif ok == 1 and i < 4:
                    quantity_name +=f"  - {product_details['product_name']} - Mã: {product_details['product_code']}"
                    quantity_name +=  " -  Giá tiền: {:,.0f} đ\n".format(product_details['lifecare_price'])
                    # quantity_name += f"  Mã kho: {product_details['product_code']}\n"
                    product = {
                            "code": product_details['product_info_id'],
                            "name": product_details['product_name'],
                            "link": product_details['file_path']
                        }
                if len(products) < 10 and product['code'] != "":
                    products.append(product)
        # else:    
        #     out_text += f"Chúng tôi không kinh doanh sản phẩm {product_name} mà anh/chị cần. Tôi có một số đề xuất mới cho  Anh/chị"
        if ok == 1:
            # out_text += f"Tôi tìm được {cnt} sản phẩm {s_name} phù hợp với nhu cầu tìm kiếm của bạn"
            out_text += f'số lượng {s_name} có {cnt} sản phẩm. Bao gồm: \n'
            out_text += quantity_name
            out_text += f"Anh/chị quan tâm chi tiết đến thông tin nào trong {cnt} sản phẩm trên?"
    if ok==0:
        out_text += f"Anh/chị có thể cho tôi biết thêm thông tin chi tiết sản phẩm  Anh/chị quan tâm để tôi có thể hỗ trợ Anh/chị được không?" 
    print("-----time elastic search-------:",time.time() - t1)
    print('======== elasticsearch output ==========:\n', out_text)
    return product_dict, out_text, products, ok