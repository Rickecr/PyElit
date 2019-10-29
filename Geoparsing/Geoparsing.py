import os
import csv
import json
import spacy
import geocoder

import nltk
from nltk.stem.porter import *
from nltk.stem import WordNetLemmatizer
from gensim.test.utils import datapath

import truecase
from googletrans import Translator

from utils import string_to_list

class Geoparsing:
    def __init__(self):
        self.translator = Translator()
        self.stemmer = PorterStemmer()
        self.nlp = spacy.load("pt_core_news_sm")
        self.nlp.Defaults.stop_words |= {"vamos", "olha", "pois", "tudo", "coisa", "toda", "tava", "pessoal", "dessa", "resolvido", "aqui", "gente", "tá", "né", "calendário", "jpb", "agora", "voltar", "lá", "hoje", "aí", "ainda", "então", "vai", "porque", "moradores", "fazer", "prefeitura", "todo", "vamos", "problema", "fica", "ver", "tô"}
        self.stop_words_spacy = self.nlp.Defaults.stop_words
        self.residential = {}
        self.gazetteer = {}
        ROOT = os.path.abspath(os.path.dirname(__file__))
        fname = ROOT + "/gazetteer/processados"
        self.gazetteer_ln = csv.DictReader(open(fname + "/gazetteer.csv", "r", encoding='utf-8'))
        self.pre_process(self.gazetteer_ln)

    def pre_process(self, gazetteer):
        for row in gazetteer:
            self.gazetteer[row['name'].lower()] = (row['coordenates'], row['fclass'])

    def remove_stop_words(self, text):
        saida = ""
        text = text.lower()
        for palavra in text.split():
            if (palavra not in self.stop_words_spacy and (len(palavra) > 3 or palavra == "rua")):
                saida += palavra + " "
        s = saida.strip()
        return s

    def concantena_end(self, lista_end):
        saida = []
        for i in range(len(lista_end) - 1):
            for j in range(i+1, len(lista_end)):
                temp = str(lista_end[i]) + " " + str(lista_end[j])
                saida.append(temp)
        return saida

    def verifica_endereco(self, end):
        # if (end['address'].lower() in ruas):
        #	return True
        if (end['confidence'] >= 5):
            # ", campina grande" in end['address'].lower() and
            if (", paraíba" in end['address'].lower()):
                return True
            else:
                return False
        else:
            return False

    def verfica(self, ents_loc, limit):
        ends = []
        for loc in ents_loc:
            l = str(loc)
            g = geocoder.arcgis(l)
            end = g.json
            if (end != None):
                ends.append(end)

        ends_corretos = []
        for e in ends:
            if (self.verifica_endereco(e)):
                ends_corretos.append(e)

        if (len(ends_corretos)):
            end_final = ends_corretos[0]
            for ed in ends_corretos:
                if (ed['confidence'] > end_final['confidence']):
                    end_final = ed
            end_ = sorted(ends_corretos, key=lambda end: end['confidence'])
            return (True, end_[0:limit])
        else:
            return (False, [])

    def search_next_index(self, lista):
        for i in range(len(lista)):
            if lista[i]['type_class'] == "geral":
                return i
        
        return len(lista) - 1

    def insert_ordened_to_priority(self, result, address, type_):
        if address not in result:
            if type_ == "school":
                address['type_class'] = "school"
                result.insert(0, address)
            elif type_ == "residential":
                address['type_class'] = "residential"
                result.insert(self.search_next_index(result), address)
            else:
                address['type_class'] = "geral"
                result.append(address)

    def choose_best_addresses(self, adresses):
        """
        Realiza a escolha dos melhores endereços encontrados.

        Parâmetro:
        ----------
        adresses : Dict
            - Dicionário de endereços e suas respectivas coordenadas.

        Retorno:
        ----------
        result : List
            - lista de dicionários de `melhores` endereços e suas respectivas coordenadas.
        """
        # TODO: Implementar algoritmos que escolham os melhores endereços
        # (x) 0: Ordenar por níveis de prioridades.
        # (x) 1: Filtrar por endereços que estejam em um determinado bairro
        # que também esteja nestes endereços.
        # ( ) 2: Olhar qual endereço mais se repete no texto.
        # ( ) 3: Aplicar os três algoritmos acima. E etc.
        
        # Olha qual endereço mais se repete no texto.
        # Ex: { "rua joão sergio": 3 }
        print(adresses.keys())
        result = []
        # Adicionar os endereços por ordem de prioridades.
        for loc in adresses.keys():
            coord, type_ = adresses[loc]
            lat, lon = string_to_list(coord)
            loc_= str(lat) + ", " + str(lon)
            g = geocoder.reverse(location=loc_, provider="arcgis")
            g = g.json
            result.append(g)
            self.insert_ordened_to_priority(result, g, type_)
        
        for a in result:
            if (a == None):
                result.remove(a)

        for a in result:
            print(a['address'], a['raw']['address']['District'])
        print("---------------------")
        # Ordenando os endereços por endereços que também foram encontrados seus bairros, 
        # assim possuindo uma chance maior de ser o endereço correto.
        new_result = []
        for i in range(len(result) - 1, -1, -1):
            l = result[i]
            if l['raw']['address']['District'].lower() in adresses.keys():
                new_result.insert(0, l)
            else:
                new_result.append(l)

        for a in new_result:
            print(a['address'], a['raw']['address']['District'])

        return result

    def filterAddressCGText(self, text):
        """
        Realiza a filtragem dos endereços do texto que estão no gazetteer.

        Parâmetro:
        ----------
        text : String
            - Texto que para realizar o geoparsing.

        Retorno:
        ----------
        result : Dict
            - Dicionário de endereços e suas respectivas coordenadas.
        """
        addresses_residentials = {}
        addresses_geral = {}

        for address in self.gazetteer.keys():
            address_aux = address.split()
            if address_aux[0] == "rua":
                address_aux = address_aux[1:]
            if len(address_aux) > 1 or self.gazetteer[address][1] == "suburb":
                address = address.replace("(", "")
                address = address.replace(")", "")
                if re.search("\\b" + address + "\\b", text):
                    print(address)
                    addresses_geral[address] = self.gazetteer[address]

        result = self.choose_best_addresses(addresses_geral)
        return result

    def geoparsing(self, text, case_correct=None, limit=5, gazetteer_cg=True):
        """
        Realiza o geoparsing do texto.

        Parâmetro:
        ----------
        text : String
            - Texto que para realizar o geoparsing.
        case_correct: Bool
            - Caso o texto já esteja com o case correto, True, caso contrário False.
        limit: Int
            - Limite máximo de endereços retornados.
        gazetteer_cg: Bool
            - Caso deseje utilizar o gazetteer da região de Campina Grande.

        Retorno:
        ----------
        result : List
            - Lista de endereços.
        """
        if (case_correct):
            if gazetteer_cg:
                result = self.filterAddressCGText(text.lower())
                if result:
                    return result
                else:
                    raise Exception("Não foi possível realizar o geoparsing do texto")        
            else:
                doc = self.nlp(text)
                ents_loc = [entity for entity in doc.ents if entity.label_ == "LOC" or entity.label_ == "GPE"]
                address_found = self.concantena_end(ents_loc)
                result = self.verfica(address_found, limit)
                if (result[0]):
                    return result[1]
                else:
                    raise Exception("Não foi possivel realizar o geoparsing do texto")
        else:
            text_en = self.translator.translate(text, src="pt", dest="en")
            text_en = text_en.text
            text_true_case = truecase.caser.get_true_case(text_en)

            text_pt = self.translator.translate(text_true_case, src="en", dest="pt")
            text = text_pt.text

            doc = self.nlp(text)

            ents_loc = [entity for entity in doc.ents if entity.label_ == "LOC" or entity.label_ == "GPE"]
            address_found = self.concantena_end(ents_loc)
            result = self.verfica(address_found, limit)

            if (result[0]):
                return result[1]
            else:
                raise Exception("Não foi possivel realizar o geoparsing do texto")

g = Geoparsing()

text = "vamos falar de coisa boa hoje tem comemoração no calendário JPB festa porque tem carimbo de Resolvido antes mesmo do esperado ela em Santa Rita moradores de tibiri reclamavam de uma cratera no meio da rua e não era só isso não quando chovia a água invade as casas uma falta de infraestrutura geral Então bora mostrar como é que tá lá Bruno você já ouviu aquele ditado Quem te viu quem te vê pois ele se aplica muito bem aqui Avenida Conde em junho quando o calendário JPB chegou aqui o Desmantelo era grande agora a gente não pode mais nem ficar muito tempo na rua porque olha só o trânsito tá fluindo Normalmente quando nós chegamos aqui a Rua Claro que estava interditada Então vamos para calçada que tem gente com força hoje aqui o Aluízio o senhor que entrou dentro do buraco comigo exatamente Não entendi o que você falou na televisão no dia certo e foi atendido mas o presente é porque hoje era para a gente voltar aqui para quem sabe ver o início da obra e hoje o calendário volta e já vê a obra pronta em uma mulher brava naquele dia ele clama Por que a gente sofre muito aqui sofreu muito o senhor voltou para sua casa tem uma briga desde fevereiro que comecei Desde o ano passado com o ex-prefeito de Netinho né E hoje foi concluído com através da TV Cabo Branco é o mesmo que a gente chamou e ela fez presente hoje trabalho está concluído o problema aqui não era pequeno não gente era muito grande a tubulação de água estava exposta a tubulação de esgoto tava exposta a tubulação de drenagem tava toda destruída e o que acontecia quando chovia a água ia toda para dentro da casa dos moradores se a gente reparar todas as casas aqui tem uma Molekinha para a gente entrar o outro lado olha só vou pedir para o Cardoso mostrar além de uma calçada bem alta A moradora ainda construiu esses batentes essas muletinhas e a informação que eu tenho é que não encheu mais de água na tubulação as maneiras que era de 200 toda substituída por 800 então o volume de água a vazão de água que suporta quatro vezes mais agora gente eu vou chamar a secretária de infraestrutura porque assim o calendário deu aquela força mas foi ela juntamente com a equipe que pode resolver com boa vontade esse problemão da vida de vocês secretária chega para cá e agora é Problema resolvido Chegamos aqui cumprimos a missão o que os soldados refizemos a tubulação colocamos de novo calçamento como vocês podem ver e assim isso tudo diante dos pedidos da população que a gente tá atendendo de acordo com as possibilidades com São Pedro a chuva a gente vem fazendo tudo que é possível nessa gestão mais vezes que a comida"
a = g.geoparsing(text=text, case_correct=True)
# print(a)
print(len(a))

# text = "hora equipe reportagem conjunto Severino Cabral bairro liberdade Feirinha fizemos reportagem acontecendo asfaltou ruas colocou sinalização preocupados acontecendo acidentes agente sério volta equipe reportagem Severino Cabral volta Damião mostrar circular mostrar feirinha Severino Cabral Bodocongó Severino Cabral continua hein francinaldo' verdade existe vieram setembro aconteceu acidentes grave recente cara chocou moto moto ficou carro preocupado pena verdade tomar providências aconteça objeto sinalização entender deles mostrar presta atenção olhada lisinha asfalto novinho folha sinalização consigo marquinha tinta branca verdade justamente preocupado acidente acidente ônibus carro moto entra asfaltada francinaldo' Providência tomada estamos preocupado namorado daqui localidade difícil comigo tentando atravessar cruzamento faixa pedestre carro passa prioridade carros param causa comércio senhor precisa atravessar medo claro medo perigoso acidente ficou precisa quebra-mola veículos passam muita velocidade ficha asfaltada faixa pedestre faixa pedestre mestre pedestres atravessar segurança placa cruzamentos indicar dona Gerusa contando situação ônibus

# textos_limpos = []
# titulos = []
# arq = csv.DictReader(open("../dados/textos_videos.csv", "r", encoding='utf-8'))

# sucess = 0
# fail = 0
# total = 0
# for p in arq:
#     try:
#         r = g.geoparsing(text=p['texto'], case_correct=True)
#         # print(r)
#         total += 1
#         sucess += 1
#     except Exception as error:
#         total += 1
#         fail += 1
#         # print(error)

# print("Total: ", total)
# print("Sucess: ", sucess)
# print("Fail: ", fail)

# for e in r:
#     print(e['address'])
#     print(e['confidence'])
#     print("----------------------")
# print(r)
