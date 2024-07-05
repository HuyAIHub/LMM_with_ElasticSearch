import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi import FastAPI, UploadFile, Form, File
import requests
import time,os
from chat import predict_rasa_llm
from ChatBot_Extract_Intent.config_app.config import get_config
from get_product_inventory import get_inventory
from ChatBot_Extract_Intent.module.google_search import search_google
import aiofiles,httpx
config_app = get_config()

app = FastAPI()
numberrequest = 0
object_tmp = ''
@app.post('/llm')
async def post(
    InputText: str = Form(None),
    IdRequest: str = Form(...),
    NameBot: str = Form(...),
    User: str = Form(...),
    GoodsCode: str = Form(None),
    ProvinceCode: str = Form(None),
    PriceSearch: str = Form(None),
    DescribeSearch: str = Form(None),
    Image: UploadFile = File(None),
    Voice: UploadFile = File(None)
):
    start_time = time.time()
    global numberrequest
    global object_tmp
    numberrequest += 1
    print("numberrequest", numberrequest)
    
    results = {
        "products": [],
        "product_similarity": [],
        "terms": [],
        "inventory_status": False,
        "similarity_status": False,
        "content": "",
        "status": 200,
        "message": "",
        "time_processing": ''
    }
    url = "http://10.248.243.105:8000/process_image_and_voice/"
    # Case 1: Image is provided
    if Image:
        image_path = os.path.join('./images', Image.filename)
        async with aiofiles.open(image_path, 'wb') as out_file:
            content = await Image.read()
            await out_file.write(content)
            
        # image_data = await Image.read()
       
        
        # Prepare the files and data to be sent
        with open(image_path, "rb") as f_image:
          files = {"data_type": f_image}
          data = {"type": "image"}
          response = requests.post(url, data=data, files=files)
          if response.status_code == 200:
              process_image = response.json()
              print(process_image)
              results["content"] = process_image
          return results
        
    if Voice:
        voice_path = os.path.join('./voices', Voice.filename)
        async with aiofiles.open(voice_path, 'wb') as out_file:
            content = await Voice.read()
            await out_file.write(content)

        with open(voice_path, "rb") as f_wav:
            files = {"data_type": f_wav}
            data = {"type": "voice"}
            response = requests.post(url,data=data, files=files)

            if response.status_code == 200:
                process_voice = response.json()
                print('speech_2_text:',process_voice)
            # predict llm
            chat_out = predict_rasa_llm(process_voice, IdRequest, NameBot, User)

            results.update({
                "content": chat_out['out_text'],
                "terms": chat_out['terms'],
                "inventory_status": chat_out['inventory_status']
            })
            # tim san pham
            print('results:',results)
            return results
    
    elif InputText not in ('terms', None) and InputText != 'similarity_status_true':
        print('check 1')
        chat_out = predict_rasa_llm(InputText, IdRequest, NameBot, User)
        object_tmp = chat_out['object_product']
        results.update({
            "content": chat_out['out_text'],
            "terms": chat_out['terms'],
            "inventory_status": chat_out['inventory_status'],
            "products" : chat_out['products'],
        })
        
    elif InputText == 'similarity_status_true':
        results['similarity_status'] = True
        results['content'] = 'Bạn hãy nhập thông tin về giá hoặc thông số kỹ thuật của sản phẩm ' + object_tmp + ' bạn đang quan tâm:'
    
    elif PriceSearch or DescribeSearch:
        search_simi =  search_google(object_tmp, PriceSearch, DescribeSearch)
        results['product_similarity'] = search_simi
            
        results.update({
            "content": 'Tôi đã tìm được những sản phẩm tương tự mà bạn có thể quan tâm:/n',
        })   
    # Case 4: GoodsCode is provided and InputText is None
    elif GoodsCode and InputText is None:
        results['content'] = get_inventory(GoodsCode, ProvinceCode)
    
    elif InputText == 'terms' or InputText == None:
        results["terms"] = config_app['parameter']['rasa_bottom']
        results["content"] = (
            "Xin chào! Mình là trợ lý AI của bạn tại VCC. "
            "Mình đang phát triển nên không phải lúc nào cũng đúng. "
            "Bạn có thể phản hồi để giúp mình cải thiện tốt hơn. "
            "Mình sẵn sàng giúp bạn với câu hỏi về chính sách và tìm kiếm sản phẩm. "
            "Hôm nay bạn cần mình hỗ trợ gì không?"
        )
    
    # Set processing time and return results
    results['time_processing'] = time.time() - start_time
    print(results)
    print('object_tmp:',object_tmp)
    return results

# uvicorn.run(app, host="0.0.0.0", port=int(config_app['server']['port']))
uvicorn.run(app, host="0.0.0.0", port=1111)