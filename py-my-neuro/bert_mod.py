import requests

class Bert_panduan:

    def __init__(self):
        self.url = 'http://127.0.0.1:6007/classify'

    def vl_bert(self,content):
        """判断输入是否需要启动视觉"""

        para = {"text": content}
        response = requests.post(self.url, json=para)

        dict_data = response.json()
        bert_output = dict_data['Vision']
        #print(bert_output)
        return bert_output

if __name__ == '__main__':
    bert = Bert_panduan()
    data = bert.vl_bert('我好无聊啊')
    print(data)