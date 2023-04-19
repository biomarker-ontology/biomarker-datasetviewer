import os,sys
from flask_restx import Namespace, Resource, fields
from flask import (request, current_app)
from glyds.document import get_one, get_many, get_ver_list, order_json_obj
from werkzeug.utils import secure_filename
from glyds.qc import run_qc
import datetime
import time
import subprocess
import json

api = Namespace("dataset", description="Dataset APIs")

dataset_search_query_model = api.model(
    'Dataset Search Query', 
    {
        'query': fields.String(required=True, default="", description='Query string')
    }
)

dataset_historylist_query_model = api.model(
    'Dataset History List Query',
    {
        'query': fields.String(required=True, default="", description='Query string')
    }
)

dataset_detail_query_model = api.model(
    'Dataset Detail Query',
    {
        'bcoid': fields.String(required=True, default="GLY_000001", description='BCO ID'),
        'dataversion': fields.String(required=False, default="1.12.1", description='Dataset Release [e.g: 1.12.1]'),
    }
)

dataset_upload_query_model = api.model(
    'Dataset Upload Query',
    {
        "format":fields.String(required=True, default="", description='File Format [csv/tsv]'),
        "qctype":fields.String(required=True, default="", description='QC Type [basic/single_glyco_site]'),
        "dataversion":fields.String(required=True, default="", description='Data Release [e.g: 1.12.1]')
    }
)

dataset_submit_query_model = api.model(
    'Dataset Submit Query',
    {
        'fname': fields.String(required=True, default="", description='First name'),
        'lname': fields.String(required=True, default="", description='Last name'),
        'email': fields.String(required=True, default="", description='Email address'),
        'affilation': fields.String(required=True, default="", description='Affilation')
    }
)

glycan_finder_query_model = api.model(
    'Glycan Finder Query',
    {
        'filename': fields.String(required=True, default="", description='File name')
    }
)

dataset_historydetail_query_model = api.model(
    'Dataset History Detail Query',
    {
        'bcoid': fields.String(required=True, default="GLY_000001", description='BCO ID')
    }
)

pagecn_query_model = api.model(
    'Dataset Page Query',
    {
        'pageid': fields.String(required=True, default="faq", description='Page ID')
    }
)

init_query_model = api.model(
    'Init Query',
    {
    }
)


ds_model = api.model('Dataset', {
    'id': fields.String(readonly=True, description='Unique dataset identifier'),
    'title': fields.String(required=True, description='Dataset title')
})





@api.route('/search')
class DatasetList(Resource):
    '''f dfdsfadsfas f '''
    @api.doc('search_datasets')
    @api.expect(dataset_search_query_model)
    #@api.marshal_list_with(ds_model)
    def post(self):
        '''Search datasets'''
        req_obj = request.json
        if req_obj["searchtype"] == "metadata":
            req_obj["coll"] = "c_extract"
            res_obj = get_many(req_obj)
            n = len(res_obj["recordlist"])
            res_obj["stats"] = {"total":n, "retrieved":n}
            return res_obj
        else:
            res = get_many({"coll":"c_extract", "query":""})
            bco_dict = {}
            for obj in res["recordlist"]:
                bco_dict[obj["bcoid"]] = {
                    "filename":obj["filename"],
                    "categories":obj["categories"],
                    "title":obj["title"]
                }
            req_obj = request.json
            req_obj["coll"] = "c_records"
            res = get_many(req_obj)
            out_dict = {}
            for obj in res["recordlist"]:
                prefix, bco_idx, file_idx, row_idx = obj["recordid"].split("_")
                bco_id = prefix + "_" + bco_idx
                bco_title, file_name = bco_dict[bco_id]["title"], bco_dict[bco_id]["filename"]
                o = {
                    "recordid":obj["recordid"],
                    "bcoid":bco_id, "fileidx":file_idx,
                    "filename":file_name, "title":bco_title,
                    "categories":bco_dict[bco_id]["categories"],
                    "rowlist":[]
                }
                if bco_id not in out_dict:
                    out_dict[bco_id] = o
                out_dict[bco_id]["rowlist"].append(int(row_idx))

            res_obj = {"recordlist":[]}
            for bco_id in out_dict:
                res_obj["recordlist"].append(out_dict[bco_id])

            n = len(res_obj["recordlist"])
            res_obj["stats"] = {"total":n, "retrieved":n}
            return res_obj


@api.route('/detail')
class DatasetDetail(Resource):
    '''Show a single dataset item'''
    @api.doc('get_dataset')
    @api.expect(dataset_detail_query_model)
    #@api.marshal_with(ds_model)
    def post(self):
        '''Get single dataset object'''
        req_obj = request.json
        
        ver_list = get_ver_list(req_obj["bcoid"])
        
        req_obj["coll"] = "c_extract"
        extract_obj = get_one(req_obj)
        if "error" in extract_obj:
            return extract_obj
       
        res = get_many({"coll":"c_records", "query":req_obj["bcoid"]})
        row_list_one, row_list_two = [], []
        for obj in res["recordlist"]:
            row_idx = int(obj["recordid"].split("_")[-1])
            if row_idx in  req_obj["rowlist"]:
                row_list_one.append(obj["row"])
            else:
                row_list_two.append(obj["row"])


        if extract_obj["record"]["sampledata"]["type"] == "table":
            extract_obj["record"]["alldata"]["data"] = []
            header_row = []
            for obj in extract_obj["record"]["sampledata"]["data"][0]:
                header_row.append(obj["label"])
            extract_obj["record"]["alldata"] = {"type":"table", "data":[]}
            extract_obj["record"]["resultdata"] = {"type":"table", "data":[]}
            extract_obj["record"]["resultdata"]["data"].append(header_row)
            extract_obj["record"]["alldata"]["data"].append(header_row)
            extract_obj["record"]["resultdata"]["data"] += row_list_one
            extract_obj["record"]["alldata"]["data"] += row_list_two
        elif extract_obj["record"]["sampledata"]["type"] == "html":
            extract_obj["record"]["alldata"] = {"type":"html", "data":"<pre>"}
            extract_obj["record"]["resultdata"] = {"type":"html", "data":"<pre>"}
            r_list_one, r_list_two = [], []
            for row in row_list_one:
                r_list_one.append("\n>"+row[-1]+"\n"+row[0])
            for row in row_list_two:
                r_list_two.append("\n>"+row[-1]+"\n"+row[0])
            extract_obj["record"]["resultdata"]["data"] = "\n".join(r_list_one)
            extract_obj["record"]["alldata"]["data"] = "\n".join(r_list_two)


        extract_obj["record"].pop("sampledata")

        req_obj["coll"] = "c_history"
        req_obj["doctype"] = "track"
        history_obj = get_one(req_obj)
        if "error" in history_obj:
            return history_obj

        
        history_dict = {}
        for ver in history_obj["record"]["history"]:
            if ver in ver_list:
                history_dict[ver] = history_obj["record"]["history"][ver]


        req_obj["coll"] = "c_bco"
        req_obj["bcoid"] = "https://biocomputeobject.org/%s" % (req_obj["bcoid"])
        bco_obj = get_one(req_obj)
        if "error" in bco_obj:
            return bco_obj

        SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
        json_url = os.path.join(SITE_ROOT, "conf/config.json")
        config_obj = json.load(open(json_url))
        #return list(bco_obj["record"].keys())
        bco_obj["record"] = order_json_obj(bco_obj["record"], config_obj["bco_field_order"])
        #return list(bco_obj["record"].keys())
        res_obj = {
            "status":1,
            "record":{
                "extract":extract_obj["record"], 
                "bco":bco_obj["record"], 
                "history":history_dict
            }
        }

        return res_obj


@api.route('/pagecn')
class Dataset(Resource):
    '''Get static page content '''
    @api.doc('get_dataset')
    @api.expect(pagecn_query_model)
    #@api.marshal_with(ds_model)
    def post(self):
        '''Get static page content '''
        req_obj = request.json
        req_obj["coll"] = "c_html"
        res_obj = get_one(req_obj)
        return res_obj


@api.route('/historylist')
class HistoryList(Resource):
    '''Get dataset history list '''
    @api.doc('historylist')
    @api.expect(dataset_historylist_query_model)
    #@api.marshal_list_with(ds_model)
    def post(self):
        '''Get dataset history list '''
        req_obj = request.json
        req_obj["coll"] = "c_history"
        req_obj["query"] = "" if "query" not in req_obj else req_obj["query"]

        hist_obj = get_many(req_obj)
        if "error" in hist_obj:
            return hist_obj
        res_obj = {"tabledata":{"type": "table","data": []}}
        header_row = [
            {"type": "string", "label": "BCOID"}
            ,{"type": "string", "label": "File Name"}
            ,{"type": "number", "label": "Field Count"}
            ,{"type": "number", "label": "Fields Added"}
            ,{"type": "number", "label": "Fields Removed"}
            ,{"type": "number", "label": "Row Count"}
            ,{"type": "number", "label": "Rows Count Prev"}
            ,{"type": "number", "label": "Rows Count Change"}
            ,{"type": "number", "label": "ID Count"}
            ,{"type": "number", "label": "IDs Added"}
            ,{"type": "number", "label": "IDs Removed"}
            ,{"type": "string", "label": ""}

        ]
        f_list = ["file_name", 
            "field_count", "fields_added", "fields_removed", 
            "row_count", "row_count_last", "row_count_change",
            "id_count", "ids_added", "ids_removed"
        ]
        res_obj["tabledata"]["data"].append(header_row)
        for obj in hist_obj["recordlist"]:
            if "history" in obj:
                ver_one = req_obj["dataversion"]
                ver_two = ver_one.replace(".", "_")
                if ver_two in obj["history"]:
                    row = [obj["bcoid"]]
                    for f in f_list:
                        row.append(obj["history"][ver_two][f])
                    row.append("<a href=\"/%s/%s/history\">details</a>" % (obj["bcoid"],ver_one))
                    match_flag = True
                    idx_list = []
                    if req_obj["query"] != "":
                        q = req_obj["query"].lower()
                        for v in [row[0].lower(), row[1].lower()]:
                            idx_list.append(v.find(q))
                        match_flag = False if idx_list == [-1,-1] else match_flag

                    if match_flag == True:
                        res_obj["tabledata"]["data"].append(row)


        return res_obj


@api.route('/historydetail')
class HistoryDetail(Resource):
    '''Show a single dataset history object'''
    @api.doc('get_dataset')
    @api.expect(dataset_historydetail_query_model)
    #@api.marshal_with(ds_model)
    def post(self):
        '''Get single dataset history object'''
        req_obj = request.json
        req_obj["coll"] = "c_history"
        res_obj = get_one(req_obj)
        if "error" in res_obj:
            return res_obj

        res_obj["record"]["history"] = res_obj["record"]["history"][req_obj["dataversion"].replace(".","_")]
        return res_obj



@api.route('/init')
class Dataset(Resource):
    '''Get init '''
    @api.doc('get_dataset')
    @api.expect(init_query_model)
    def post(self):
        '''Get init '''
        req_obj = request.json
        req_obj["coll"] = "c_init"
        res_obj = get_one(req_obj)
        return res_obj



@api.route('/upload', methods=['GET', 'POST'])
class DatasetUpload(Resource):
    '''Upload dataset item'''
    @api.doc('upload_dataset')
    @api.expect(dataset_upload_query_model)
    #@api.marshal_with(ds_model)
    def post(self):
        '''Upload dataset'''
        res_obj = {}
        req_obj = request.form
        error_obj = {}
        if request.method != 'POST':
            error_obj = {"error":"only POST requests are accepted"}
        elif 'userfile' not in request.files and 'file' not in request.files:
            error_obj = {"error":"no file parameter given"}
        else:
            file = request.files['userfile'] if "userfile" in request.files else request.files['file']
            file_format = req_obj["format"]
            qc_type = req_obj["qctype"]
            data_version = req_obj["dataversion"]
            file_data = []
            if file.filename == '':
                error_obj = {"error":"no filename given"}
            else:
                file_name = secure_filename(file.filename)
                data_path, ser = os.environ["DATA_PATH"], os.environ["SERVER"]
                out_file = "%s/userdata/%s/tmp/%s" % (data_path, ser, file_name)
                file.save(out_file)
                res_obj = {
                    "inputinfo":{"name":file_name, "format":file_format}, 
                    "summary":{"fatal_qc_flags":0, "total_qc_flags":0},
                    "failedrows":[]
                }

                error_obj = run_qc(out_file, file_format, res_obj, qc_type, data_version)
        res_obj = error_obj if error_obj != {} else res_obj
        return res_obj


@api.route('/submit')
class Dataset(Resource):
    '''Submit dataset '''
    @api.doc('get_dataset')
    @api.expect(dataset_submit_query_model)
    def post(self):
        '''Submit dataset '''
        req_obj = request.json
        data_path, ser = os.environ["DATA_PATH"], os.environ["SERVER"]
        src_file = "%s/userdata/%s/tmp/%s" % (data_path, ser, req_obj["filename"])
        dst_dir = "%s/userdata/%s/%s" % (data_path, ser, req_obj["affilation"])
        if os.path.isfile(src_file) == False:
            res_obj = {"error":"submitted filename does not exist!", "status":0}
        else:
            if os.path.isdir(dst_dir) == False:
                dst_dir = "%s/userdata/%s/%s" % (data_path, ser, "other")
            today = datetime.datetime.today()
            yy, mm, dd = today.year, today.month, today.day
            dst_file = "%s/%s_%s_%s_%s" % (dst_dir, mm, dd, yy, req_obj["filename"])
            json_file = ".".join(dst_file.split(".")[:-1]) + ".json"

            cmd = "cp %s %s" % (src_file, dst_file)
            x, y = subprocess.getstatusoutput(cmd)
            if os.path.isfile(dst_file) == False:
                res_obj = {"error":"save file failed!", "status":0}
            else:
                res_obj = {"confirmation":"Dataset file has been submitted successfully!", "status":1}
                with open(json_file, "w") as FW:
                    FW.write("%s\n" % (json.dumps(req_obj, indent=4)))
        return res_obj



@api.route('/glycan_finder')
class Dataset(Resource):
    '''Glycan Finder '''
    @api.doc('get_dataset')
    @api.expect(glycan_finder_query_model)
    def post(self):
        '''Glyca Finder '''
        req_obj = request.json
        data_path, ser = os.environ["DATA_PATH"], os.environ["SERVER"]
        uploaded_file = "%s/userdata/%s/tmp/%s" % (data_path, ser, req_obj["filename"])
        
        output_file = "%s/userdata/%s/tmp/%s_output_%s.txt" % (data_path, ser, req_obj["filename"], os.getpid())

        if os.path.isfile(uploaded_file) == False:
            res_obj = {"error":"submitted filename does not exist!", "status":0}
        else:
            file_format = req_obj["filename"].split(".")[-1]
            cmd = "sh /hostpipe/glycan_finder.sh %s %s" % (uploaded_file, output_file)
            glycan_list = []
            if ser != "dev":
                glycan_list = subprocess.getoutput(cmd).strip().split(",")
            else:
                glycan_list = ["A", "B"]
                time.sleep(5)

            res_obj = {
                "inputinfo":{"name":req_obj["filename"], "format":file_format},
                "mappingrows":[
                    [
                        {"type": "string", "label": "GlyToucan Accession"},
                        {"type": "string", "label": "Glycan Image"}
                    ]
                ]
            }
            for ac in glycan_list:
                link_one = "<a href=\"https://glygen.org/glycan/%s\" target=_>%s</a>" % (ac,ac)
                link_two = "<a href=\"https://gnome.glyomics.org/restrictions/GlyGen.StructureBrowser.html?focus=%s\" target=_>related glycans</a>" % (ac)
                img = "<img src=\"https://api.glygen.org/glycan/image/%s\">" % (ac)
                links = "%s (other %s)" % (link_one, link_two)
                res_obj["mappingrows"].append([links, img])

        return res_obj


