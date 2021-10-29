

def is_equal_path_segment_list(path_segment_list_1, path_segment_list_2):
    if len(path_segment_list_1) != len(path_segment_list_2):
        return False
    for idx, path_segment in enumerate(path_segment_list_1):
        if len(path_segment) != len(path_segment_list_2[idx]):
            return False
        for idx2, switch in enumerate(path_segment):
            if switch != path_segment_list_2[idx][idx2]:
                return False
    return True

def new_RSP_id(SP_list):
    # if len(SP_list.keys()) == 0:
    #     return 0
    cur_RSP_num = 0
    for k in SP_list:
        cur_RSP_num += len(SP_list[k].keys())
    return cur_RSP_num