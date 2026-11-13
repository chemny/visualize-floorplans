"""Independent synthetic UI fixtures, never a suggested or approved home layout."""
import copy


def regression_cases():
    def wall(id, a, b, bearing=True, thickness=200, opens=None):
        return dict(id=id, a=a, b=b, t=thickness, height=2800, bearing=bearing, opens=opens or [])

    def item(id, kind, x, y, w, d, h, rot=0, **extra):
        return dict(id=id, type=kind, name=kind, cx=x, cy=y, w=w, d=d, h=h,
                    rot=rot, elevation=0, color='#d2c4ae', **extra)

    def room(id, name, poly, role):
        return dict(id=id, name=name, poly=poly, at=[sum(p[0] for p in poly)/len(poly),
                    sum(p[1] for p in poly)/len(poly)], function=role, material='wood')

    def make(key, footprint, rooms, walls, furniture):
        cid = 'synthetic-cross-layout-' + key
        for r in rooms:
            # Explicit lamp anchors stay inside each fixture's room rectangle.
            x, y = r['at']
            furniture.append(item('lamp-'+r['id'], 'ceilinground', x, y, 500, 500, 60,
                                  mount='ceiling', lightOn=True, lightIntensity=3,
                                  lightTemperature=3500))
            furniture[-1]['elevation'] = 2740
        width, depth = max(p[0] for p in footprint), max(p[1] for p in footprint)
        case = {'schema':'floor-visualization-case/1.0', 'caseId':cid,
                'syntheticFixture':{'purpose':'Independent cross-layout regression only',
                                    'notApprovedLayout':True, 'variant':key},
                'referenceNote':'Synthetic test fixture, not a client apartment or approval.',
                'model':{'title':'合成测试', 'width':width, 'depth':depth, 'height':2800,
                         'footprint':footprint, 'rooms':rooms},
                'initialState':{'version':12, 'caseId':cid, 'style':'champagne_pearl',
                    'rooms':{r['id']:{'name':r['name'], 'function':r['function'],
                                     'mat':'antislip' if r['function']=='bathroom' else 'wood'} for r in rooms},
                    'walls':walls, 'furniture':furniture, 'doors':{}, 'measures':[],
                    'demolished':[], 'ceilings':[], 'wallFinishes':{}},
                'references':{}, 'presentation':{'materials':{'marble':{'veins':False}}}}
        return {'name':key, 'case':case,
                'checks':'core,components,floors',
                'requiredPass':['copy','header','sidebars','lighting','view','floors'] +
                               (['generated','components'] if len(rooms)>1 else []),
                'requiredMechanisms':['shower','vanity','bathtub','door'] if len(rooms)>1 else [],
                'expectedNotApplicable':['generated','components','plan-order'] if len(rooms)==1 else []}

    footprint = [[0,0],[10000,0],[10000,7000],[0,7000]]
    rooms = [room('zone-a91','起居',[[100,100],[4930,100],[4930,6900],[100,6900]],'living'),
             room('zone-b37','盥洗',[[5070,100],[9900,100],[9900,6900],[5070,6900]],'bathroom')]
    walls = [wall('edge-'+str(i), a, footprint[(i+1)%4]) for i,a in enumerate(footprint)]
    walls += [wall('divider-a',[5000,0],[5000,7000],False,140,
                   [{'id':'hinged-a','kind':'door','at':2700,'width':1000,
                     'hingeEnd':'start','swing':1,'angle':110}])]
    walls[0]['opens'] = [{'id':'slide-a','kind':'sliding','at':1300,'width':1600,
                          'height':2100,'leaves':1,'slideMount':'wall','slideSide':1,
                          'slideDirection':1,'slideOpen':0,'slideOverlap':20}]
    furniture = [item('seat-a','sofa',2200,5400,2200,850,850),
                 item('work-a','desk',2200,1700,1200,600,750),
                 item('tucked-a','chair',2200,2125,450,450,850,180),
                 item('store-a','wardrobe',5700,4100,1500,600,2200,90),
                 item('glass-a','shower',6500,1400,900,900,2100,
                      showerDoor={'type':'hinged','hinge':'left','angle':90,'open':0,'width':860}),
                 item('wash-a','vanity',8500,1400,900,550,850),
                 item('tub-a','bathtub',7900,5400,1700,800,600)]
    rectangle = make('rectangle-renamed',footprint,rooms,walls,furniture)
    rectangle['case']['model']['floorConnections'] = [
        {'id':'threshold-a','materialRoomId':'zone-a91',
         'poly':[[4930,2700],[5070,2700],[5070,3700],[4930,3700]]}]

    footprint = [[0,0],[10000,0],[10000,5000],[6000,5000],[6000,9000],[0,9000]]
    rooms = [room('n7-main','起居',[[100,100],[5930,100],[5930,4930],[100,4930]],'living'),
             room('n2-wet','卫浴',[[6070,100],[9900,100],[9900,4900],[6070,4900]],'bathroom'),
             room('s8-rest','寝室',[[100,5070],[5900,5070],[5900,8900],[100,8900]],'bedroom')]
    walls = [wall('outline-'+str(i), a, footprint[(i+1)%len(footprint)]) for i,a in enumerate(footprint)]
    walls += [wall('divider-b',[6000,0],[6000,5000],False,140,
                   [{'id':'hinged-b','kind':'door','at':2300,'width':1000,
                     'hingeEnd':'end','swing':-1,'angle':135}]),
              wall('divider-c',[0,5000],[6000,5000],False,140,
                   [{'id':'slide-b','kind':'sliding','at':2700,'width':1600,
                     'height':2100,'leaves':1,'slideMount':'wall','slideSide':-1,
                     'slideDirection':-1,'slideOpen':.4,'slideOverlap':20}])]
    furniture = [item('long-b','cabinet',1500,1300,1200,450,1800,180),
                 item('work-b','desk',3900,1500,1300,650,750,90),
                 item('tucked-b','chair',3450,1500,450,450,850,-90),
                 item('glass-b','shower',7100,1400,900,900,2100,90,
                      showerDoor={'type':'hinged','hinge':'right','angle':90,'open':0,'width':860}),
                 item('wash-b','vanity',8500,3400,900,550,850,-90),
                 item('tub-b','bathtub',3600,7600,1700,800,600,180),
                 item('bed-b','bed',1600,7100,1500,2050,1000)]
    concave = make('concave-rotated',footprint,rooms,walls,furniture)
    concave['case']['model']['floorConnections'] = [
        {'id':'threshold-b','materialRoomId':'n7-main',
         'poly':[[5930,2300],[6070,2300],[6070,3300],[5930,3300]]},
        {'id':'threshold-c','materialRoomId':'n7-main',
         'poly':[[2700,4930],[4300,4930],[4300,5070],[2700,5070]]}]

    footprint = [[0,0],[4000,0],[4000,3500],[0,3500]]
    rooms = [room('only-q6','空间',[[100,100],[3900,100],[3900,3400],[100,3400]],'living')]
    walls = [wall('shell-'+str(i), a, footprint[(i+1)%4]) for i,a in enumerate(footprint)]
    minimal = make('single-empty',footprint,rooms,walls,[])
    # Intentionally no ceiling fixtures: tests must report unavailable operations.
    minimal['case']['initialState']['furniture'] = []
    return copy.deepcopy([rectangle, concave, minimal])
