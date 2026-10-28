import math
import unittest
from tour_speed_profile import profile,sample,coupled_clock,spatial_time,assemble


class SpeedProfileTests(unittest.TestCase):
    def test_straight_path_stops_at_exact_endpoints(self):
        p=profile([[0,0],[2400,0]])
        self.assertEqual(p['speed'][0],0)
        self.assertEqual(p['speed'][-1],0)
        self.assertEqual(sample(p,0),[0,0])
        self.assertAlmostEqual(sample(p,p['seconds'])[0],2400)
        self.assertLessEqual(max(p['speed']),1200)

    def test_collinear_subdivision_does_not_create_extra_stops(self):
        a=profile([[0,0],[2400,0]])
        b=profile([[x,0] for x in range(0,2401,150)])
        self.assertAlmostEqual(a['seconds'],b['seconds'],places=8)

    def test_local_gaze_cost_cannot_hide_in_whole_connection_maximum(self):
        p={'time':[0,1,10]}
        y=[0,math.pi/2,math.pi/2]
        clock=coupled_clock(p,y,30)
        self.assertGreater(clock[-1],12)
        self.assertAlmostEqual(spatial_time(p,clock,clock[1]),1)
        self.assertEqual(spatial_time(p,clock,clock[-1]),10)

    def test_optional_clock_reserve_does_not_raise_actual_yaw_limit(self):
        p={'time':[0,1]};y=[0,math.pi/2]
        exact=coupled_clock(p,y,30,0)
        self.assertAlmostEqual(exact[-1],3)
        self.assertGreater(coupled_clock(p,y,30)[-1],exact[-1])
        for bad in [-.001,.051,float('nan'),True]:
            with self.assertRaises(ValueError):coupled_clock(p,y,30,bad)

    def test_invalid_settling_reserve_is_rejected_before_planning(self):
        for bad in [-.01,.51,float('nan'),True]:
            with self.assertRaises(ValueError):assemble(None,{}, {'clockSettleSeconds':bad})

    def test_invalid_gaze_anchors_are_rejected(self):
        with self.assertRaises(ValueError):coupled_clock({'time':[0,1]},[0],32)
        with self.assertRaises(ValueError):coupled_clock({'time':[0,1]},[0,1],0)


class FrozenFragmentTests(unittest.TestCase):
    def fixture(self):
        import copy
        from types import SimpleNamespace
        chapters=[{'name':'first','phase':'observe','from':'a','to':'b'},
                  {'name':'connection','phase':'transit','from':'b','to':'c'},
                  {'name':'second','phase':'observe','from':'c','to':'d'}]
        frames=[{'frame':i,'pointMm':[0 if i<=6 else min(10,(i-6)*10/6),0],
                 'yawRadians':0.,'pitchRadians':0.,'eyeMm':1600,
                 'horizontalFovDegrees':76,'shiftY':0} for i in range(19)]
        for i in range(12,19):frames[i]['pointMm']=[10,0]
        tour={'fps':24,'seconds':19/24,'frames':frames,
              'visits':[{'name':k,'frame':i} for k,i in zip('abcd',[0,6,12,18])]}
        engine=SimpleNamespace(c={'chapters':chapters,'timingLocks':{'totalFrames':19}},
            fps=24,m=dict(zip('abcd',[0,6,12,18])),t=tour,entry=copy.deepcopy(frames[0]),
            limits={'maximumSpeedMps':1.2,'maxYawDegreesPerSecond':32,'maxPitchDegreesPerSecond':14})
        def forbidden(*args):raise AssertionError('A frozen fragment must not be replanned')
        engine.connection_path=forbidden
        windows={'a':copy.deepcopy(frames[:7]),'c':copy.deepcopy(frames[12:])}
        return engine,windows,{'connection':copy.deepcopy(frames[6:13])}

    def test_matching_frozen_connection_is_preserved_without_replanning(self):
        e,w,f=self.fixture()
        result,config,report=assemble(e,w,{'preserveObservationPositions':True},f)
        self.assertEqual(result['frames'],e.t['frames'])
        self.assertEqual(report['frozenTransitChapters'],['connection'])
        self.assertTrue(all(v['sourcePositionsFrozen'] for v in report['observationReparameterization']))

    def test_stale_frozen_connection_is_rejected(self):
        for field,value in [('pointMm',[2,0]),('yawRadians',.01),('pitchRadians',.01),
                            ('eyeMm',1650),('horizontalFovDegrees',80),('shiftY',.05)]:
            with self.subTest(field=field):
                e,w,f=self.fixture();f['connection'][0][field]=value
                with self.assertRaisesRegex(ValueError,'Frozen transit'):
                    assemble(e,w,{'preserveObservationPositions':True},f)

    def test_unknown_or_incomplete_frozen_fragment_is_rejected(self):
        e,w,f=self.fixture()
        with self.assertRaisesRegex(ValueError,'existing transit'):
            assemble(e,w,{}, {'missing':f['connection']})
        with self.assertRaisesRegex(ValueError,'endpoint context'):
            assemble(e,w,{}, {'connection':f['connection'][:1]})


if __name__=='__main__':unittest.main()
