
import os,re
from difflib import get_close_matches
import csv

with open('ChatBot_Extract_Intent/data/product_final_204_oke.xlsx - Sheet1.csv', 'r') as file:
    reader = csv.DictReader(file)
    data = list(reader)

def process_command(demands,list_product):
    print('======process_command======')
    lst_mua = ['mua','quan tâm','giá','tìm','thích','bán', 'xem','liệt kê']
    lst_so_luong = ['số lượng','bao nhiêu','mấy loại']
    # demands = extract_info(command)

    # if ((demands['demand'].lower() in lst_mua) and len(demands['value']) >= 1) or (len(demands['value']) >= 1 and len(demands['object']) > 0 and len(demands['demand']) == 0):
    #     return [0, handle_buy(demands)]
    # elif (demands['demand'].lower() in lst_mua) and len(demands['value']) == 0:
    #     return handle_interest(demands)
    # elif demands['demand'].lower() in lst_so_luong:
    #     return handle_count(demands)
    if (demands['demand'].lower() in lst_mua) and len(demands['value']) >= 1:
        return [0, handle_buy(demands)]
    elif (demands['demand'].lower() in lst_mua) and len(demands['value']) == 0:
        return [0, handle_interest(demands)]
    elif demands['demand'].lower() in lst_so_luong:
        return [0, handle_count(demands)]
    else:
        return handle_tskt(demands, list_product)
    
def handle_count(demands):
    print('======handle_count======')
    # Xử lý yêu cầu về số lượng sản phẩm
    matching_products = []
    for product in data:
        group_name = product['GROUP_PRODUCT_NAME'].lower()
        if any(demands["object"][0].lower() in group_name for obj in demands["object"]):
            if demands["value"]:
                specifications = re.sub(r'[^a-zA-Z0-9]', '', product['SPECIFICATION_BACKUP'].lower())
                if re.sub(r'[^a-zA-Z0-9]', '', demands["value"].lower()) in specifications:
                    matching_products.append(product)
            else:
                matching_products.append(product)


    # Trả kết quả vào một chuỗi
    result_string = ""
    if matching_products:
        result_string += f"Số lượng {', '.join(demands['object'])} {demands['value']}: {len(matching_products)} sản phẩm\n"
    else:
        # Tìm các giá trị gần đúng với "value" trong cột SPECIFICATION_BACKUP
        value_possibilities = set(re.sub(r'[^a-zA-Z0-9]', '', product['SPECIFICATION_BACKUP'].lower()) for product in data)
        close_matches = get_close_matches(re.sub(r'[^a-zA-Z0-9]', '', demands["value"].lower()), value_possibilities)

        if close_matches:
            result_string += f"Không tìm thấy {' '.join(demands['object'])} {demands['value']} trong dữ liệu.\n"
            result_string += f"Có thể bạn muốn tìm kiếm:\n"
            for match in close_matches:
                result_string += f"- {' '.join(demands['object'])} {match.title()}\n"
        else:
            result_string += f"Không tìm thấy {' '.join(demands['object'])} {demands['value']} trong dữ liệu."

    return result_string