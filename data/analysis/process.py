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

annotation2foa = {"Waiting for feedback": ("Tablet", "Secondary tablet", "Facilitator"),
        "Writing word": ("Tablet", "Robot"),
        "Waiting for word to write": ("Secondary tablet",),
        "Story telling": ("Robot",),
        "Presentation": ("Robot",),
        "robot": ("Robot",),
        "tablet": ("Tablet",),
        "facilitator": ("Facilitator",),
        "selection": ("Secondary tablet",),
        "observer": ("Observer",),
        "paper": ("Secondary tablet",), # is that correct?
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

def get_previous_observation_start(start, timestamps):
    for idx, t in enumerate(timestamps):
        if start < t:
            yield timestamps[idx-1] if (idx-1) >= 0 else timestamps[0]

def withmeness(observed, expected):

    total_time = 0.
    total_time_matching = 0.

    # we iterate primarily on the *expected* targets of attention
    for idx, t_expected_start in enumerate(expected.keys()):

        targets, t_expected_end = expected[t_expected_start]

        total_time += t_expected_end - t_expected_start

        # then, for each time period, we iterate over the actual observation,
        # starting at the last observation *before* the considered period.
        for t_obs_start in get_previous_observation_start(t_expected_start, observed.keys()):

            target, t_obs_end = observed[t_obs_start]

            # if the observation starts *after* the considered period, we move
            # to the next period, ie the next 'expected' targets
            if t_obs_start > t_expected_end: 
                break

            # if the observation ends *before* the considered period (it may be
            # the case, since we start with the last observation which started
            # before the period), we skip it.
            if t_obs_end < t_expected_start:
                continue

            # if the observed target is one of the expected one, add the actual
            # observation time *for this period* to total_time_matching
            if target[0] in targets:
                print("Match at %s!" % t_obs_start)
                start = max(t_expected_start, t_obs_start)
                end = min(t_expected_end, t_obs_end)
                total_time_matching += end - start
            else:
                print("Mismatch at %s" % t_obs_start)

    withmeness = total_time_matching/total_time
    print("Total time: %s sec, total time matching: %s sec, With-me-ness: %s" % (total_time, total_time_matching, withmeness))

    return withmeness

withmeness(events_observed, events_expected)
