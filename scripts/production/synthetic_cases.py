"""Small, explicitly synthetic workbench fixtures; no client drawing or approval."""
def fixture_cases():
    def room(id,poly,name):return {'id':id,'name':name,'poly':poly,'at':[sum(p[0] for p in poly)/len(poly),sum(p[1] for p in poly)/len(poly)],'material':'marble'}
    def wall(id,a,b,bearing=True):return {'id':id,'a':a,'b':b,'t':120,'height':2800,'bearing':bearing,'opens':[]}
    def lamp(id,x,y):return {'id':id,'name':'合成测试主灯','type':'ceilinground','cx':x,'cy':y,'w':500,'d':500,'h':60,'elevation':2740,'rot':0,'color':'#fbfaf7','mount':'ceiling','lightOn':True,'lightIntensity':3,'lightTemperature':3500}
    cases=[]
    for kind in ['rectangle','concave']:
        if kind=='rectangle':
            width,depth=6000,4000;foot=[[0,0],[6000,0],[6000,4000],[0,4000]]
            rooms=[room('left',[[120,120],[2940,120],[2940,3880],[120,3880]],'测试书房'),room('right',[[3060,120],[5880,120],[5880,3880],[3060,3880]],'测试客厅')]
            walls=[wall('outer'+str(i),p,foot[(i+1)%4]) for i,p in enumerate(foot)]+[wall('partition',[3000,0],[3000,4000],False)]
            walls[-1]['opens']=[{'id':'test-door','kind':'door','at':2500,'width':850,'hingeEnd':'start','swing':1,'angle':90}]
            furniture=[lamp('lamp-left',1500,1800),lamp('lamp-right',4500,1800),{'id':'desk','type':'desk','name':'合成测试书桌','cx':1300,'cy':600,'w':1200,'d':600,'h':750,'elevation':0,'rot':0,'color':'#d5c4a9'}]
        else:
            width,depth=6000,5000;foot=[[0,0],[6000,0],[6000,2500],[3000,2500],[3000,5000],[0,5000]]
            rooms=[room('L',[[120,120],[5880,120],[5880,2380],[2880,2380],[2880,4880],[120,4880]],'测试转角客厅')]
            rooms[0]['at']=[1500,2000];walls=[wall('outer'+str(i),p,foot[(i+1)%6]) for i,p in enumerate(foot)];furniture=[lamp('lamp-a',1500,1500),lamp('lamp-b',4400,1400),lamp('lamp-c',1500,4000)]
        cid='synthetic-beta4-'+kind
        cases.append({'schema':'floor-visualization-case/1.0','caseId':cid,'referenceNote':'Synthetic test fixture, not a reconstructed or approved apartment.','model':{'title':'合成测试 · '+kind,'width':width,'depth':depth,'height':2800,'footprint':foot,'rooms':rooms},'initialState':{'version':12,'caseId':cid,'style':'champagne_pearl','rooms':{r['id']:{'name':r['name'],'mat':'marble'} for r in rooms},'walls':walls,'furniture':furniture,'doors':{},'measures':[],'demolished':[],'ceilings':[],'wallFinishes':{}},'areaMetadata':{'suite':width*depth/1e6,'gross':None,'note':'Synthetic bounding box only'},'presentation':{'materials':{'marble':{'veins':False}}},'walkStart':{'roomId':rooms[0]['id'],'point':[1700,2800],'lookAt':[1600,500],'eyeMm':1600},'references':{}})
    import copy
    stress=copy.deepcopy(cases[0]);stress['caseId']='synthetic-beta4-stress';stress['initialState']['caseId']=stress['caseId'];stress['model'].update(title='合成照明与家具压力场景',width=12000,depth=9000,footprint=[[0,0],[12000,0],[12000,9000],[0,9000]])
    rooms=[];furniture=[]
    for y in range(3):
        for x in range(3):
            rid=f'r{x}-{y}';poly=[[x*4000+120,y*3000+120],[(x+1)*4000-120,y*3000+120],[(x+1)*4000-120,(y+1)*3000-120],[x*4000+120,(y+1)*3000-120]]
            rooms.append(room(rid,poly,'测试区域 '+rid));furniture.append(lamp('main-'+rid,x*4000+2000,y*3000+1500))
            for k in range(12):furniture.append({'id':f'chair-{rid}-{k}','type':'chair','name':'合成测试椅子','cx':x*4000+550+(k%4)*850,'cy':y*3000+450+(k//4)*750,'w':450,'d':480,'h':860,'elevation':0,'rot':k*30,'color':'#c4bbaa'})
            for k in range(2):furniture.append({'id':f'sconce-{rid}-{k}','type':'walllamp','name':'合成辅助灯','cx':x*4000+400+k*3200,'cy':y*3000+450,'w':200,'d':80,'h':220,'elevation':1800,'rot':0,'color':'#f6eee3','mount':'wall','lightOn':True,'lightIntensity':1.5,'lightTemperature':3000})
    foot=stress['model']['footprint'];walls=[wall('outer'+str(i),p,foot[(i+1)%4]) for i,p in enumerate(foot)]+[wall('vertical'+str(i),[i*4000,0],[i*4000,9000],False) for i in [1,2]]+[wall('horizontal'+str(i),[0,i*3000],[12000,i*3000],False) for i in [1,2]]
    stress['model']['rooms']=rooms;stress['initialState'].update(rooms={r['id']:{'name':r['name'],'mat':'marble'} for r in rooms},walls=walls,furniture=furniture);stress['walkStart']={'roomId':rooms[0]['id'],'point':[2000,2600],'lookAt':[2000,500],'eyeMm':1600};stress['areaMetadata']['suite']=108;cases.append(stress)
    return cases
if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    from h5 import build
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args();root=Path(args.out);root.mkdir(exist_ok=False,parents=True)
    for c in fixture_cases():
        case=root/(c['caseId']+'.json');case.write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8');build(case,root/(c['caseId']+'.html'))
    print(root)
