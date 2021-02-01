import numpy as np
import pandas as pd
import time, datetime
import os, sys, glob



if __name__=='__main__':
    print(f"Compiling data logs from remote units...")
    while True:
        try:   
            for n in ['T1', 'H1', 'H2', 'H3', 'H4', 'H5']: 
                t = time.perf_counter()
                
                newfiles = glob.glob(f'/home/pi/studies/ardmore/temp/{n}_*.pkl.xz')
                

                if len(newfiles):
                    newfiles.sort(key=os.path.getmtime)
                    newfiles = newfiles[::-1]
                    newfiles = np.array(newfiles)
                    newfiles = newfiles[:100]
                    print(newfiles)
                    unixstart = float(newfiles[0].split('_')[-1].split('.')[0])/1000
                    unixend = unixstart + (86400)
                    endfile = f'/home/pi/studies/ardmore/temp/{n}_{unixend*1000}.pkl.xz'
                    newfiles = newfiles[newfiles<endfile]

                    dt_start = datetime.datetime.fromtimestamp(unixstart)
                    today = dt_start.strftime('%Y_%m_%d')
                    
                    oldfiles = glob.glob(f'/home/pi/studies/ardmore/data/{n}_{today}.pkl.xz')
                    
                    df_all = pd.DataFrame()
                    if oldfiles: 
                        try:
                            df_all = pd.read_pickle(oldfiles[-1])
                            if 'timestamp' in df_all.columns:
                                df_all.rename(columns={'timestamp':'unixtime'}, inplace=True)
                            # print(df_all.head(3))
                        except Exception as e:
                            print(e)
                            pass
                            
                        
                    
                    for nf in newfiles:
                        try:
                            df_new = pd.read_pickle(nf)
                            if 'timestamp' in df_new.columns:
                                df_new.rename(columns={'timestamp':'unixtime'}, inplace=True)
                            
                            df_all = pd.concat([df_all, df_new], axis=0)
                        except:
                            print(nf)
                            pass
                    
                    
                    df_all.dropna(inplace=True, subset=['unixtime'])
                    df_all['unixtime'] = df_all['unixtime'].astype(int)
                    df_all = df_all.groupby('unixtime').mean()
                    df_all.reset_index(drop=False, inplace=True)
                    if df_all.size:
                        df_all.tail(3600*24).to_pickle(f'/home/pi/studies/ardmore/data/{n}_{today}.pkl.xz')
                        # print(pd.read_pickle(f'/home/pi/studies/ardmore/data/{n}_{today}.pkl.xz').head(10))
                        [os.system(f'rm {x}') for x in newfiles]
                        # print(time.perf_counter()-t)
                
        except Exception as e:
            print(f"Error:{e}")
            pass
        except KeyboardInterrupt:
            break