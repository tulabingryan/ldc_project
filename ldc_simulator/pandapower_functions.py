import pandapower as pp
import pandapower.networks as nw
from pandapower.pf.runpp_3ph import runpp_3ph

### pandapower helper functions
def convert_to_3ph(net):
  ### update external grid
  net.ext_grid["r0x0_max"] = 0.1
  net.ext_grid["x0x_max"] = 1.0
  net.ext_grid["s_sc_max_mva"] = 10000
  net.ext_grid["s_sc_min_mva"] = 8000
  net.ext_grid["rx_min"] = 0.1
  net.ext_grid["rx_max"] = 0.1
  
  ### update transformer
  net.trafo = net.trafo.head(0)
  pp.create_std_type(net, {"sn_mva": 0.3, "vn_hv_kv": 20, "vn_lv_kv": 0.4, "vk_percent": 6,
              "vkr_percent": 0.78125, "pfe_kw": 2.7, "i0_percent": 0.16875,
              "shift_degree": 0, "vector_group": "YNyn",
              "tap_side": "hv", "tap_neutral": 0, "tap_min": -2, "tap_max": 2,
              "tap_step_degree": 0, "tap_step_percent": 2.5, "tap_phase_shifter": False,
              "vk0_percent": 6, "vkr0_percent": 0.78125, "mag0_percent": 100,
              "mag0_rx": 0., "si0_hv_partial": 0.9,}, 
              "YNyn", "trafo")
  
  pp.create_transformer(net, 0, 1, std_type="YNyn", parallel=1,tap_pos=0,
                          index=pp.get_free_id(net.trafo))
  net.trafo.reset_index()
  
  ### add zero sequence for lines
  net.line["r0_ohm_per_km"] = 0.0848
  net.line["x0_ohm_per_km"] = 0.4649556
  net.line["c0_nf_per_km"] = 230.6
  
  ### convert loads to asymmertric loads
  for i in net.load.index:
    row = net.load.loc[i]
    phases = [0,0,0]
    p = i % 3
    phases[p] = 1
    pp.create_asymmetric_load(net, row['bus'], 
               p_a_mw=row['p_mw']*phases[0], q_a_mvar=row['q_mvar']*phases[0], 
               p_b_mw=row['p_mw']*phases[1], q_b_mvar=row['q_mvar']*phases[1],
               p_c_mw=row['p_mw']*phases[2], q_c_mvar=row['q_mvar']*phases[2], 
               sn_mva=row['sn_mva'])
    
  net.load['p_mw'] = 0
  net.load['q_mvar'] = 0
  pp.add_zero_impedance_parameters(net)
  return net

