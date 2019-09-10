# ハーベスタ本体
from datetime import datetime, date, timedelta
from tqdm import tqdm
import time
import os
import xml.etree.ElementTree as ET
import urllib.request

import time
import codecs
from io import StringIO,BytesIO

#XMLの名前空間
OAI='{http://www.openarchives.org/OAI/2.0/}'
dc ='{http://purl.org/dc/elements/1.1/}'
dcndl='{http://ndl.go.jp/dcndl/terms/}'
dcterms='{http://purl.org/dc/terms/}'
rdf='{http://www.w3.org/1999/02/22-rdf-syntax-ns#}'
rdfs='{http://www.w3.org/2000/01/rdf-schema#}'
foaf='{http://xmlns.com/foaf/0.1/}'

#ElementTree(xmlを解析するライブラリ)にも名前空間を登録
ET.register_namespace('',"http://www.openarchives.org/OAI/2.0/")
ET.register_namespace('rdf', "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
ET.register_namespace('rdfs', "http://www.w3.org/2000/01/rdf-schema#")
ET.register_namespace('dc',"http://purl.org/dc/elements/1.1/")
ET.register_namespace('dcterms',"http://purl.org/dc/terms/")
ET.register_namespace('dcndl',"http://ndl.go.jp/dcndl/terms/")
ET.register_namespace('xsi',"http://www.w3.org/2001/XMLSchema-instance")
ET.register_namespace('schemaLocation',"http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd")
ET.register_namespace('oai_dc',"http://www.openarchives.org/OAI/2.0/oai_dc/")
ET.register_namespace('foaf',"http://xmlns.com/foaf/0.1/")
ET.register_namespace('owl',"http://www.w3.org/2002/07/owl#")

#proxy_support = urllib.request.ProxyHandler({'http': 'http://10.11.71.1:8080','https': 'http://10.11.71.1:8080'})
#opener = urllib.request.build_opener(proxy_support)
#urllib.request.install_opener(opener)


class OAI_harvester:
    def __init__(self, outputxmlpath="xml_all.xml", prefixname="dcndl"):
        self.outputxml = outputxmlpath
        self.prefixname = prefixname
        self.resumptiontoken = None
        self.datasize = None
        with open(self.outputxml, 'wb') as f:
            print("initialize file")

    def _parse_xml_ndl(self):
        tree = ET.parse('oaitmp.xml')
        root = tree.getroot()
        with codecs.open(self.outputxml, 'a', "utf-8") as f:
            es_item = root.find(OAI + 'ListRecords').findall(OAI + 'record')
            for item in es_item:  # OAI-PMHは「id <xml>」のようになっているので不要なid部分を消す
                if item.find(OAI + 'metadata') is None:
                    continue
                item2 = item.find(OAI + 'metadata').find(rdf + 'RDF')
                item_id = item.find(OAI + 'metadata').find(rdf + 'RDF').find(dcndl + "BibAdminResource").attrib[
                    rdf + "about"].split("/")[-1]
                item_str = ET.tostring(item2, encoding='utf8', method='xml').decode()
                item_str = item_str.replace("\n", "")
                f.write(item_str + "\n")
        if root.find(OAI + 'ListRecords') is None:
            self.resumptiontoken = None
            return
        token = root.find(OAI + 'ListRecords').find(OAI + "resumptionToken")
        if token is None or token.text is None:
            self.resumptiontoken = None
            return
        self.datasize = token.attrib["completeListSize"]
        self.resumptiontoken = token.text

    def _download_xml(self, fromdate):
        # b = io.BytesIO()
        with open("oaitmp.xml", 'wb') as f:
            url = "http://iss.ndl.go.jp/api/oaipmh?verb=ListRecords"
            if self.resumptiontoken is not None:
                url += "&resumptionToken=" + self.resumptiontoken
            else:
                url += "&from=" + fromdate + "&metadataPrefix=" + self.prefixname + "&set=" + self.setname
                print(url)
            # print(url)
            try:
                data = urllib.request.urlopen(url)
                f.write(data.read())
                http_code = data.getcode()
                if http_code == 200:
                    retval = True
                else:
                    retval = False
            except Exception as e:
                print(str(e))
                retval = False
        return retval

    def getxml(self, setname, fromdate=None):
        self.setname = setname
        self.resumptiontoken = None
        if fromdate is None:
            # 最初の200件は条件を指定して取得する。fromとuntilで年度の期間を取得できるが、最大1年分
            today = datetime.today()
            fromdate = datetime.strftime(today - timedelta(days=364), '%Y-%m-%d')
        self._download_xml(fromdate)
        self._parse_xml_ndl()
        print(self.datasize + "件見つかりました。200件ずつ取得します")
        if self.resumptiontoken is not None:
            self._parse_xml_ndl()
            for index in tqdm(range(int(self.datasize) // 200 + 1)):
                while not self._download_xml(fromdate):
                    print("retry")
                    time.sleep(1)
                # print("downloading  file_count:",index)
                self._parse_xml_ndl()
                if self.resumptiontoken is None:
                    break
        else:
            print("エラーです。set名を確認してください")

oai=OAI_harvester(outputxmlpath="xml_913.xml")
oai.getxml(setname="iss-ndl-opac-national:913",fromdate="2018-06-19")