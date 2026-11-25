import unittest
import tour_room_tiers as t

class RoomTiers(unittest.TestCase):
    def test_boundaries_belong_to_the_larger_tier(self):
        self.assertEqual([t.tier_of(a) for a in (2.1,4.99,5.0,9.99,10.0,19.99,20.0,35)],['under5','under5','5to10','5to10','10to20','10to20','over20','over20'])
    def test_smaller_rooms_get_shallower_and_quicker_looks(self):
        order=['under5','5to10','10to20','over20'];rows=[t.TIERS[n] for n in order]
        for key in ('maxEntryDepthMm','viewSeconds','maxSweepDegrees'):
            values=[r[key] for r in rows];self.assertEqual(values,sorted(values));self.assertEqual(len(set(values)),4)
    def test_case_depth_is_only_ever_stricter(self):
        self.assertEqual(t.stricter_depth(600,None),600);self.assertEqual(t.stricter_depth(600,400),400);self.assertEqual(t.stricter_depth(600,1200),600)
    def test_area_of_a_rectangle(self):
        self.assertAlmostEqual(t.area_m2([[0,0],[2000,0],[2000,2500],[0,2500]]),5.0)

    def test_retrace_budget_grows_with_the_room_and_never_drops_below_noise(self):
        self.assertEqual([t.retrace_budget(a) for a in (3,7,15,30)],[1.0,1.0,60.0,90.0])
        self.assertEqual(t.retrace_budget(15,{'10to20':25}),25.0)

if __name__=='__main__':unittest.main()
