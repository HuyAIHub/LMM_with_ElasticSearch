import time,os
from chat import predict_rasa_llm,predict_rasa_llm_for_image
from config_app.config import get_config
from utils.get_product_inventory import get_inventory
from utils.google_search import search_google
from utils.api_call import call_api
from datetime import datetime
from ChatBot_Extract_Intent.module.few_shot_sentence import find_closest_match
import pandas as pd
import logging, random
config_app = get_config()
numberrequest = 0
object_tmp = ''
data_private = config_app['parameter']['data_private']
df = pd.read_excel(data_private)
def save_file(file, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_path = os.path.join(folder, file.filename)
    with open(file_path, 'wb') as out_file:
        content = file.file.read()
        out_file.write(content)
    return file_path

def handle_request(
    InputText=None,
    IdRequest=None,
    NameBot=None,
    User=None,
    GoodsCode=None,
    ProvinceCode=None,
    ObjectSearch=None,
    PriceSearch=None,
    DescribeSearch=None,
    Image=None,
    Voice=None
    ):
    current_date = datetime.now().strftime("%Y-%m-%d")
    start_time = time.time()
    global object_tmp
    results = {
        "products": [],
        "product_similarity": [],
        "terms": [],
        "inventory_status": False,
        "similarity_status": False,
        "content": "",
        "status": 200,
        "message": "",
        "time_processing": ""
    }
    url = "http://10.248.243.105:8000/process_image_and_voice/"
    
    try:
        if Image:
            logging.info("---SEARCH_IMAGE---")
            print('----Image-----')
            img_folder = './images/' + User + '/' + current_date
            image_path = save_file(Image, img_folder)
            
            with open(image_path, "rb") as f_image:
                files = {"data_type": f_image}
                data = {"type": "image"}
                response = call_api(url, data=data, files=files)
                print('response:', response)
                try:
                    if response['status'] == 200:
                        objects = response['result']
                        chat_out = predict_rasa_llm_for_image(objects, IdRequest, NameBot, User)
                        object_tmp = chat_out['object_product']
                        results.update({
                            "content": chat_out['out_text'],
                            "terms": chat_out['terms'],
                            "inventory_status": chat_out['inventory_status'],
                            "products": chat_out['products'],
                        })
                    else:
                        results['content'] = response['message']
                except Exception as e:
                    results['content'] = response['message']
                return results
            
        if Voice:
            logging.info("---Voice---")
            print('----Voice-----')
            voice_folder = './voices/' + User + '/' + current_date
            voice_path = save_file(Voice, voice_folder)

            with open(voice_path, "rb") as f_wav:
                files = {"data_type": f_wav}
                data = {"type": "voice"}
                response = call_api(url, data=data, files=files)
                print(response)
                try:
                    if response['status'] == 200:
                        process_voice = response['result']
                        print('speech_2_text:', process_voice)
                        chat_out = predict_rasa_llm(process_voice, IdRequest, NameBot, User)
                    
                        results.update({
                            "content": chat_out['out_text'],
                            "terms": chat_out['terms'],
                            "inventory_status": chat_out['inventory_status'],
                            "products": chat_out['products'],
                        })
                except Exception as e:
                    results['content'] = response
                print('results:', results)
                return results
        
        elif InputText not in ('terms', None) and InputText != 'similarity_status_true':
            logging.info("---ChatText---")
            print('----ChatText-----')
            chat_out = predict_rasa_llm(InputText, IdRequest, NameBot, User)
            object_tmp = chat_out['object_product']
            results.update({
                "content": chat_out['out_text'],
                "terms": chat_out['terms'],
                "inventory_status": chat_out['inventory_status'],
                "similarity_status": chat_out['similarity_status'],
                "products" : chat_out['products'],
            })

        elif InputText == 'similarity_status_true':
            results['similarity_status'] = True
            results['content'] = 'Bạn hãy nhập thông tin về giá hoặc thông số kỹ thuật của sản phẩm ' + object_tmp + ' bạn đang quan tâm:'
        
        elif ObjectSearch and (PriceSearch or DescribeSearch) or ObjectSearch:
            print('ObjectSearch',ObjectSearch)
            try:
                logging.info("---Similarity---")
                print('----similarity-----')
                list_product = df["group_name"].unique()
                check_match_product = find_closest_match(ObjectSearch, list_product)
                if check_match_product[1] > 40:
                    search_simi =  search_google(ObjectSearch, PriceSearch, DescribeSearch)
                    results['product_similarity'] = search_simi
                    results.update({
                        "content": 'Tôi đã tìm được những sản phẩm tương tự mà bạn có thể quan tâm:',
                    })
            except:
                results.update({
                    "content": 'không tìm được thông tin sản phẩm tương tự mà bạn quan tâm',
                })
        # Case 4: GoodsCode is provided and InputText is None
        elif GoodsCode and InputText is None:
            logging.info("---Inventory---")
            print('----Inventory-----')
            results['content'] = get_inventory(GoodsCode, ProvinceCode)
        
        elif InputText == 'terms' or InputText == None:
            results["terms"] = config_app['parameter']['rasa_button']
            messages = [
            "Xin chào! Mình là trợ lý AI của bạn tại VCC. Mình đang phát triển nên không phải lúc nào cũng đúng. Bạn có thể phản hồi để giúp mình cải thiện tốt hơn. Mình sẵn sàng giúp bạn với câu hỏi về chính sách và tìm kiếm sản phẩm. Hôm nay bạn cần mình hỗ trợ gì không?",
            "Chào bạn! Tôi là AI hỗ trợ của VCC. Do đang trong quá trình hoàn thiện nên tôi có thể mắc lỗi. Mọi góp ý của bạn đều giúp tôi ngày càng hoàn thiện. Tôi có thể giúp gì cho bạn về các vấn đề chính sách hoặc tìm kiếm thông tin sản phẩm hôm nay?",
            "Xin chào! Là AI trợ lý tại VCC đây. Tôi vẫn đang trong giai đoạn phát triển và có thể không hoàn hảo. Hãy giúp tôi cải thiện bằng cách phản hồi về trải nghiệm của bạn. Tôi có thể hỗ trợ bạn gì về chính sách hoặc thông tin sản phẩm hôm nay?",
            "Xin chào anh/chị! Tôi rất hân hạnh được hỗ trợ anh chị trong việc tìm kiếm sản phẩm và chính sách.",
            "Rất vui khi được hỗ trợ anh/chị trong việc tìm kiếm sản phẩm. Do đang trong quá trình hoàn thiện nên tôi có thể mắc lỗi. Mong anh/chị thông cảm!"
            ]
            results["content"] = random.choice(messages)
    except Exception as e:
        # results["status"] = 500
        results["content"] = 'Rất tiếc vì sự cố không mong muốn này. Chúng tôi đang nỗ lực khắc phục và sẽ sớm trở lại. Cảm ơn sự thông cảm của bạn!'
    
    # Set processing time and return results
    # print("check object global", object_tmp)
    results['time_processing'] = time.time() - start_time
    print('results:',results)
    return results