import requests
from typing import Type, List
import os
# from kag.builder.component.reader.markdown_reader import MarkDownReader
from kag.interface import ScannerABC
from knext.common.base.runnable import Input, Output
from kag.common.conf import KAG_PROJECT_CONF   
@ScannerABC.register("feishu")
@ScannerABC.register("feishu_scanner")     
class FeishuScanner(ScannerABC):
    def __init__(self,access_token):
        """
        Initializes the FeishuScanner with the specified token, rank, and world size.

        Args:
            access_token (str): The authentication token for accessing Yuque API.
            rank (int, optional): The rank of the current worker. Defaults to 0.
            world_size (int, optional): The total number of workers. Defaults to 1.
        """
        super().__init__()
        self.access_token = access_token
        self.table_id = []
        self.count = 0
    
    @property
    def input_types(self) -> Type[Input]:
        return str
    
    @property
    def output_types(self) -> Type[Output]:
        """The type of output this Runnable object produces specified as a type annotation."""
        return str

    def get_doc(self,doc_id):
        doc_url =f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/raw_content?lang=0'
        headers = {'Authorization': f'Bearer {self.access_token}'}
        response = requests.get(doc_url,headers=headers)
        document_list = response.json()['data']['content']
        return document_list
    
    def get_all_blocks_doc(self,doc_id):
        url=f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks?document_revision_id=-1&page_size=100'
        headers = {'Authorization': f'Bearer {self.access_token}'}
        response = requests.get(url,headers=headers)
       # document_block_list = response.json()['data']['items']
        document_block = response.json()['data']
        return document_block
    
    def get_doc_title(self,block):
        title = block['page']['elements'][0]['text_run']['content']
        return title
    
    def get_text_from_elements(self, elements):
        """Extracts and concatenates text from a list of text elements."""
        text = ''
        for elem in elements:
            if 'text_run' in elem:
                text += elem['text_run'].get('content', '')
            elif 'equation' in elem:
                # For equations, we simply output the content (optionally wrap in $ if needed)
                text += f"${elem['equation'].get('content', '')[:-1]}$"
        return text
    
    def get_image_download(self,token,img_count):
        url=f'https://open.feishu.cn/open-apis/drive/v1/medias/batch_get_tmp_download_url?file_tokens={token}'
        headers = {'Authorization': f'Bearer {self.access_token}'}
        response = requests.get(url,headers=headers)
        local_file_path = os.path.join(KAG_PROJECT_CONF.ckpt_dir, "feishu_scanner")
        if not os.path.exists(local_file_path):
            os.makedirs(local_file_path)
        file_path = os.path.join(local_file_path, f'{img_count}.json')
        tmp_url = response.json()['data']['tmp_download_urls'][0]['tmp_download_url']
        resp = requests.get(tmp_url)
        with open(file_path, 'wb') as f:
            f.write(resp.content)
        return file_path
    def convert_block(self, block, blocks,  indent=''):
        """Recursively converts a single block (and its children) to Markdown."""
        markdown = ''
        bt = block.get('block_type')

        # Process block content based on its type
        if bt == 1:
            # Container / page block. It may contain a page with elements (title).
            if 'page' in block and 'elements' in block['page']:
                content = self.get_text_from_elements(block['page']['elements']).strip()
                if content:
                    markdown += indent + '# ' + content + '\n\n'
        elif bt == 2 and block.get("parent_id") not in self.table_id:
            # Paragraph block with text
            if 'text' in block and 'elements' in block['text']:
                content = self.get_text_from_elements(block['text']['elements']).strip()
                markdown += indent + content + '\n\n'
        elif bt in [3,11]: #bt 3-11 response to heading 1-9
            # Heading block (heading1) -> convert to a markdown header
            if f'heading{bt-2}' in block and 'elements' in block[f'heading{bt-2}']:
                content = self.get_text_from_elements(block[f'heading{bt-2}']['elements']).strip()
                markdown += indent + ('#' *(bt-1)) + ' ' + content + '\n\n'
        elif bt == 12:
            # Unordered list item (bullet).
            if 'bullet' in block and 'elements' in block['bullet']:
                content = self.get_text_from_elements(block['bullet']['elements']).strip()
                markdown += indent + '- ' + content + '\n'
        elif bt == 13:
            # Ordered list item
            if 'ordered' in block and 'elements' in block['ordered']:
                count = 2
                content = self.get_text_from_elements(block['ordered']['elements']).strip()
                markdown += indent + f'{count}. '+ content + '\n'
                count = count + 1
        elif bt == 14: #code item
            if 'code' in block and 'elements' in block['code']:
                content = self.get_text_from_elements(block['code']['elements']).strip()
                markdown += indent+'```'+'\n'+content+'\n'+'```'
        elif bt == 27:
            # Image block: output a markdown image and download the image using token
            if 'image' in block:
                token = block['image'].get('token', 'Image')
                markdown += indent + '![Image](' + self.get_image_download(token,self.count) + ')\n\n'
                self.count += 1
        elif bt == 31: #convert table to md
           if 'table' in block:
               table_md = "|"
               self.table_id.append(block['block_id'])
               col = block['table']['property']['column_size'] #列大小
               row = block['table']['property']['row_size']  #行大小
               for child_id in block['table']['cells']:
                   self.table_id.append(child_id)
                   index_table = block['table']['cells'].index(child_id)
                   r = int((index_table)/col)
                   c = (index_table)%col
                   table_content = self.get_text_from_elements(blocks[blocks[child_id].get('children','')[0]]['text']['elements'])+'|'
                   table_md += table_content
                   if(c== col-1):
                       table_md +='\n'
                       if(r != row-1):
                           table_md+='|'
                       if(r==0):
                           table_md += '---|'*col+'\n'+'|'
               markdown += indent + table_md              
        else:
            # Fallback: if the block has a text field, output it
            if 'text' in block and 'elements' in block['text']:
                content = self.get_text_from_elements(block['text']['elements']).strip()
                markdown += indent + content + '\n\n'

        # Process children recursively if any
        if 'children' in block and block['children'] and block['block_id'] not in self.table_id and block['parent_id'] not in self.table_id:
            # For list items, we want to indent nested children
            if bt in [12, 13]:
                child_indent = indent + '  '
            else:
                child_indent = indent
            

            for child_id in block['children']:
                child = blocks.get(child_id)
                if child:
                    markdown += self.convert_block(child, blocks=blocks, indent=child_indent)
        return markdown
    
    def convert(self, blocks):
        """Converts the entire JSON document to a Markdown string."""
        markdown = ''
        # Process blocks that are top-level (parent_id is an empty string)
        for block_id in blocks:
            if blocks[block_id].get('parent_id', '') == '':
                markdown += self.convert_block(blocks[block_id], blocks,  indent='') + '\n'
        return markdown
    
    def load_data(self,input: Input, **kwargs) -> List[Output]:    
        doc_id = input
        data = self.get_all_blocks_doc(doc_id)
        title = self.get_doc_title(data['items'][0])
        blocks = {}
        for block in data.get('items', []):
            blocks[block['block_id']] = block
        markdown_output = self.convert(blocks)
        local_file_path = os.path.join(KAG_PROJECT_CONF.ckpt_dir, "feishu_scanner")
        if not os.path.exists(local_file_path):
            os.makedirs(local_file_path)
        local_file = os.path.join(local_file_path, title+'.md')
        with open(local_file, 'w', encoding='utf-8') as f:
            f.write(markdown_output)
        return [local_file]