from collections import OrderedDict
import pympi

from simplesvg import Scene, Line


############################################################################
#     Processing of the EAF file
############################################################################

elan_file = "../4.eaf"

tier_observed = "Attention focus"
tier_expected = "Robot state"

eaf = pympi.Elan.Eaf(elan_file)

annotation2foa = {
        ##### Robot state #####
        "Waiting for feedback": ("Tablet", "Secondary tablet"),
        "Writing word": ("Tablet", "Robot"),
        "Waiting for word to write": ("Secondary tablet",),
        "Story telling": ("Robot",),
        "Presentation": ("Robot",),
        "Bye": ("Robot",),
        ##### Attention focus #####
        "robot": ("Robot",),
        "tablet": ("Tablet",),
        "facilitator": ("Facilitator",),
        "selection": ("Secondary tablet",),
        "observer": ("Observer",),
        "paper": ("Secondary tablet",), 
        "other": ("Other",)}


def get_time(ts):
    """ Returns the timestamp of an EAF 'timeslot', in seconds
    """
    return eaf.timeslots[ts] / 1000.


# First, convert all EAF timeslots into timestamp in seconds and 'normalize'
# the focus of attention using the mappings in annotation2foa
def prepare(tier):
    rawevents = {}
    for _, entry in eaf.tiers[tier][0].items():
        ts, te, ann, _ = entry

        if ann not in annotation2foa:
            print("Unknown annotation: %s" % ann)
            continue

        rawevents[get_time(ts)] = (annotation2foa[ann], get_time(te))

    # Order the 'events' by timestamps
    return OrderedDict(sorted(rawevents.items(), key=lambda t: t[0]))

events_observed = prepare(tier_observed)
events_expected = prepare(tier_expected)

############################################################################
#     SVG rendering
############################################################################

plotting_order = {"Observer": 0,
                  "Facilitator": 1,
                  "Secondary tablet": 2,
                  "Robot": 3,
                  "Tablet": 4,
                  "Other": 5}


def plot(name, events):
    svg = Scene(name)

    for ts, evt in events.items():

        targets, te = evt
        for t in targets:
            print("%s: %d to %d" % (t, ts, te))

            # a different offset for each 'target'
            offset = plotting_order[t] * 10

            # simply draw a plain line between the two timestamps
            svg.add(Line((ts, offset), (te,offset)))

    svg.write_svg()

plot("expected", events_expected)
plot("groundtruth", events_observed)

############################################################################
#     With-me-ness
############################################################################

from numpy import arange

dt = 0.1 # seconds

t_end = events_expected[events_expected.keys()[-1]][1]

def find_interval(t, intervals):
    for ts, te in intervals:
        if ts <= t and te >= t:
            return ts, te
    return None, None

def withmeness(observed, expected):

    total_time = 0.
    total_time_matching = 0.

    expected_intervals = [(k, v[1]) for k,v in events_expected.items()]
    observed_intervals = [(k, v[1]) for k,v in events_observed.items()]

    for t in arange(0, t_end, dt):
            expected_start, _ = find_interval(t, expected_intervals)
            observed_start, _ = find_interval(t, observed_intervals)

            if expected_start and observed_start:
                total_time += dt

                target = events_observed[observed_start][0][0]
                expected_targets = events_expected[expected_start][0]

                if target in expected_targets:
                    total_time_matching += dt

    withmeness = total_time_matching/total_time
    print("Total time: %s sec, total time matching: %s sec, With-me-ness: %s" % (total_time, total_time_matching, withmeness))

    return withmeness

withmeness(events_observed, events_expected)
