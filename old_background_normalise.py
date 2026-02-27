def background_normalise(request_form, request_files, session_data, RunningVals, Lookups, meta_data, streams, stream_table):
    from nodes import allelectors
    from state import Treepolys, Fullpolys, progress, DQstats
    from sklearn.metrics.pairwise import haversine_distances


    def recursive_kmeans_latlon(X, max_cluster_size, MAX_DEPTH=5, depth=0, prefix='K'):
        """
        Recursively cluster a DataFrame with 'Lat' and 'Long' columns using KMeans,
        splitting any clusters larger than max_cluster_size. Skips empty clusters.
        """
        if depth >= MAX_DEPTH:
            logger.info(f"Max depth {MAX_DEPTH} reached at cluster {prefix}, size {len(X)}")
            return {i: f"{prefix}" for i in X.index}

        if len(X) <= max_cluster_size:
            logger.debug(f"Cluster {prefix} is within size limit. Size: {len(X)}")
            return {i: f"{prefix}" for i in X.index}

        # Estimate number of clusters needed to stay under max_cluster_size
        k = min(int(np.ceil(len(X) / max_cluster_size)), len(X))  # Prevent over-splitting
        coords = X[['Lat', 'Long']].values

        logger.info(f"[Depth {depth}] Splitting {len(X)} points into {k} clusters (prefix: {prefix})")

        kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(coords)

        label_map = {}
        for i in range(k):
            idx = X.index[labels == i]

            # ✅ Skip clusters with no members
            if len(idx) == 0:
                logger.warning(f"Cluster {prefix}-{i+1} is empty. Skipping.")
                continue

            sub_data = X.loc[idx]
            new_prefix = f"{prefix}-{i+1}"

            logger.debug(f"Cluster {new_prefix} | Size: {len(sub_data)}")

            sub_labels = recursive_kmeans_latlon(
                sub_data,
                max_cluster_size=max_cluster_size,
                MAX_DEPTH=MAX_DEPTH,
                depth=depth + 1,
                prefix=new_prefix
            )
            label_map.update(sub_labels)

        return label_map

    try:

        # Simulate step progress throughout your pipeline
        # All your existing code from the route goes here, replacing request.form/files/session

        # ⚠️ Use `request_form`, `request_files`, and `session_data` instead of Flask globals
        # e.g. replace `request.form` → `request_form`
        # e.g. replace `session['current_node_id']` → `session_data['current_node_id']`



        # Setup logger
        logging.basicConfig(
            filename = "electtrek.log",
            level=logging.INFO,  # or INFO
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        logger = logging.getLogger(__name__)

        # 6. Process metadata for all files in selected stream( does not have to be current election)
        file_index = 0
        mainframes = []
        deltaframes = []
        aviframes = []
        DQstatslist =[]
        mainframe = pd.DataFrame()
        deltaframe = pd.DataFrame()
        aviframe = pd.DataFrame()
        DQstats = pd.DataFrame()

        progress["percent"] = 0
        progress["status"] = "sourcing"
        progress["message"] = "Sourcing data from instruction files ..."


        print("___Route/normalise: ",meta_data.items())
        total = len(meta_data)
        for idx, (index, data) in enumerate(sorted(meta_data.items(), key=lambda x: int(x[1]['order']))):
            progress["percent"] = int((idx / total) * 100)
            progress["status"] = "processing"
            progress["message"] = f"Processing sourced data (file {idx + 1} of {total})..."

            print(f"\nRow index {index} data {data}")

            stream = str(data.get('election', '')).upper()
            ELECTIONS = get_available_elections()
            if stream not in ELECTIONS:
                progress["percent"] = 100
                progress["status"] = "error"
                progress["message"] = f"Error: Election '{stream}' not recognized {ELECTIONS}."
                print(progress["message"])
                return

            print(f"___Selected {stream} election and session node id: ", session_data.get('current_node_id',"UNITED_KINGDOM"))
            SelectedElection = CurrentElection.load(stream)  # essential for election specific processing

            order = int(data.get('order'))
            filetype = data.get('type')
            purpose = data.get('purpose')
            try:
                fixlevel = int(data.get('fixlevel', 0))
            except ValueError:
                fixlevel = 0
            file_path = data.get('saved_path') or data.get('stored_path', '')

            print(f"Election: {stream}")
            print(f"Order: {order}")
            print(f"Type: {filetype}")
            print(f"Purpose: {purpose}")
            print(f"Fixlevel: {fixlevel}")
            print(f"File path: {file_path}")

            if not file_path or not os.path.exists(file_path):
                print(f"❌ File path does not exist: {file_path}")
                continue  # skip to next file

            formdata = {}
            ImportFilename = str(file_path)
            print("_____ reading file outside normz",ImportFilename)
            print("🔍 type of json2:", type(json))
            if os.path.exists(TABLE_FILE):
                with open(TABLE_FILE) as f:
                    stream_table = json.load(f)
            else:
                stream_table = []
        # Collect all possible unique stream names for dropdowns
            streams = sorted(set(row['election'] for row in stream_table))
            streamrag = {}
            dfx = pd.DataFrame()

            try:
                if file_path and os.path.exists(file_path):
                    progress["percent"] = 0
                    progress["status"] = "Running"
                    progress["message"] = f"Reading file{file_path}"

                    if file_path.upper().endswith('.CSV'):
                        print("readingCSVfile outside normz", file_path)
                        dfx = pd.read_csv(
                            file_path,
                            sep=',',                   # Use comma as the separator
                            encoding='ISO-8859-1'      # Keep this if needed for special characters
                        )
                    elif file_path.upper().endswith('.XLSX'):
                        print("readingEXCELfile outside normz", file_path)
                        dfx = pd.read_excel(file_path, engine='openpyxl')
                    else:
                        e="error-Unsupported file format"
                        print(e)
                        progress["percent"] = 100
                        progress["status"] = "error"
                        progress["message"] = f"Error: {str(e)}"
                        return
                    if "EventDate" in dfx.columns:
                        dfx["EventDate"] = pd.to_datetime(dfx["EventDate"], errors="coerce")
                    progress["percent"] = 5
                    progress["status"] = "Running"
                    progress["message"] = f"File injested {file_path}"

                else:
                    print("error - File path does not exist or is not provided: ", file_path)
                    progress["percent"] = 100
                    progress["status"] = "error"
                    progress["message"] = f"Error file path: {file_path}"
                    return
            except Exception as e:
                print("error-file access exception:",str(e))
                tb = traceback.format_exc()
                print("❌ Exception in background_normalise:", e)
                print(tb)
                progress["percent"] = 100
                progress["status"] = "error"
                progress["message"] = f"Error: {str(e)}"
                return
    # progress update finished sorting through instructions,  now starting normalisation stream data
            progress["election"] = stream
            progress["status"] = "running"
            progress["percent"] = 0
            progress["message"] = "Starting normalisation..."

    # normz delivers [normalised elector data df,stats dict,original data quality stats in df]
            Outcomes = pd.read_excel(GENESYS_FILE)
            Outcols = Outcomes.columns.to_list()
            if purpose == "main":
            # this is one of the main index files (1+)
                progress["percent"] = 25
                progress["status"] = "running"
                progress["message"] = "Normalising main file :"+ ImportFilename
                results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                temp = pd.DataFrame(results[0],columns=Outcols)
                mainframes.append(temp)
                DQstatslist.append(results[1])
            elif purpose == 'delta':
            # this is one of many changes that may  be applied to the main index
                progress["percent"] = 40
                progress["status"] = "running"
                progress["message"] = "Normalising delta files :"+ImportFilename
                if 'ElectorCreatedMonth' in dfx.columns:
                    dfx = dfx[dfx['ElectorCreatedMonth'] > 0] # extract all new registrations
                    results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                    temp = pd.DataFrame(results[0],columns=Outcols)
                    deltaframes.append(temp)
                    DQstatslist.append(results[1])
                else:
                    progress["percent"] = 60
                    progress["status"] = "completing"
                    progress["message"] = "Normalising delta files :"+ImportFilename
                    print("NO NEW REGISTRATIONS IN DELTA FILE", dfx.columns)
                    results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                    temp = pd.DataFrame(results[0],columns=Outcols)
                    deltaframes.append(temp)
                    DQstatslist.append(results[1])
            elif purpose == 'avi':
            # this is an addition of columns to the main index
                progress["percent"] = 60
                progress["status"] = "running"
                progress["message"] = "Normalising avi file :"+ImportFilename
                results = normz(progress,RunningVals,Lookups,stream,ImportFilename,dfx,fixlevel, purpose)
                temp = aviframe[['ENOP','AV']]
                aviframes.append(temp)
                DQstatslist.append(results[1])
            elif purpose == 'resource':
                progress["percent"] = 60
                progress["status"] = "running"
                progress["message"] = "Normalising resource file ..."
                if os.path.exists(file_path) and os.path.getsize(file_path) and file_path.upper().endswith('.CSV'):
                    print("readingCSVfile resources outside normz", file_path)
                    dfx = pd.read_csv(file_path,sep='\t',engine='python',encoding='ISO-8859-1')
                elif os.path.exists(file_path) and os.path.getsize(file_path) and file_path.upper().endswith('.XLSX'):
                    print("readingEXCELfile resources outside normz", file_path)
                    dfx = pd.read_excel(file_path, engine='openpyxl')
                required_columns = ['Code','Email','Mobile','Status','Address1', 'Address2', 'Postcode', 'Firstname','Surname']
                if not all(col in dfx.columns.tolist() for col in required_columns):
                    raise ValueError(f"Not all {dfx.columns.tolist()} in {required_columns}")
                print(f"___Resources {len(dfx)} imported: {dfx.columns}")
            elif purpose == 'mark':
                progress["percent"] = 60
                progress["status"] = "running"
                progress["message"] = "Normalising resource file ..."
                if os.path.exists(file_path) and os.path.getsize(file_path) and file_path.upper().endswith('.CSV'):
                    print("readingCSVfile markers outside normz", file_path)
                    dfx = pd.read_csv(file_path,sep='\t',engine='python',encoding='ISO-8859-1')
                elif os.path.exists(file_path) and os.path.getsize(file_path) and file_path.upper().endswith('.XLSX'):
                    print("readingEXCELfile markers outside normz", file_path)
                    dfx = pd.read_excel(file_path, engine='openpyxl')
                required_columns = ['EventDate','AddressPrefix','Address1','Address2','Postcode','url','Lat','Long']

                if not all(col in dfx.columns.tolist() for col in required_columns):
                    raise ValueError(f"Not all {dfx.columns.tolist()} in {required_columns}")
                print(f"___Markers {len(dfx)} imported: {dfx.columns}")

    # full stream now received - need to apply changes to main

        fullsum = sum(len(x) for x in mainframes + deltaframes + aviframes)

        if fixlevel == 3:
            for DQ in DQstatslist:
                DQstats = pd.concat([DQstats, DQ])

            for i,mf in enumerate(mainframes):
                progress["percent"] = round(((i + 1) / len(mainframes)) * 100, 2)
                progress["status"] = "running"
                progress["message"] = "Pipelining normalised delta files ..."
                print("__Processed main,delta,avi electors:", len(mf), len(deltaframes),len(aviframe), mf.columns)
                mainframe = pd.concat([mainframe, pd.DataFrame(mf)], ignore_index=True)
                len1 = len(mf)
                print("__Processed mainframe electors:", len(mf), mf.columns)


            for i,df in enumerate(deltaframes):
                progress["percent"] = round(((i + 1) / len(mainframes)) * 100, 2)
                progress["status"] = "running"
                progress["message"] = "Pipelining normalised delta files ..."
                print("_____Deltaframe Details:", df)
                for index, change in df.iterrows():
                    print("_____Delta Change Details:", change)
                mainframe = pd.concat([mainframe, pd.DataFrame(df)], ignore_index=True)
                print("__Processed deltaframe electors:", len(df), df.columns)

            for i,af in enumerate(aviframes):
                progress["percent"] = 85
                progress["status"] = "running"
                progress["message"] = "Pipelining normalised avi file ..."
                print(f"____compare merge length before: {len1} after {len(mainframe)}")
                mainframe = mainframe.merge(af, on='ENOP',how='left', indicator=True )
                mainframe = mainframe.rename(columns= {'AV_y': 'AV'})
                af.to_csv("avitest.csv",sep='\t', encoding='utf-8', index=False)
                print("__Processed aviframe:", len(af), af.columns)

            progress["percent"] = 90
            progress["status"] = "running"
            progress["message"] = "Normalised all source files now clustering ..."

            mainframe = pd.DataFrame(mainframe,columns=Outcols)

            current_election = stream
            CElection = CurrentElection.load(current_election)
            current_node = get_last_node(current_election,CElection)
            rlevels = CElection.resolved_levels
            print('___persisting file ', ELECTOR_FILE, len(allelectors))
            allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)


            territory_path = CElection['mapfiles'][-1] # this is the node at which the imported data is to be filtered through
            Territory_node = current_node.ping_node(rlevels,current_election,territory_path, create=True)
            ttype = Territory_node.child_type(rlevels)
            #        Territory_node = self
            #        ttype = electtype
            pfile = Treepolys[ttype]
            Territoryboundary = pfile[pfile['FID']== int(Territory_node.fid)]

            print(f"____Territory limited to :{territory_path} for election {current_election}")

            PDs = set(mainframe.PD.values)
            frames = []
            for PD in PDs:
                mask = mainframe['PD'] == PD
                PDelectors = mainframe[mask]
                print(f"__PD: {PD} PDElectors: {len(PDelectors)}")
                PDmaplongx = PDelectors.Long.mean()
                PDmaplaty = PDelectors.Lat.mean()
                print(f"____PD: {PD} Postcode: {PDelectors['Postcode'].iloc[0]} lat: {PDmaplaty}, long: {PDmaplongx} at node:",Territory_node.value, Territory_node.fid)
    # Need to add L4-AREA value - for all PDs - pull together all PDs which are within the area(ward or division) boundary
                spot = Point(float('%.6f'%(PDmaplongx)),float('%.6f'%(PDmaplaty)))

                areatypecolumn = {
                    '-DIVS.html': 'division',
                    '-MAP.html': 'ward',
                    '-WARDS.html': 'ward',
                    '-MAP.html': 'constituency'
                }

                if Territoryboundary.geometry.contains(spot).item():
                    if Territory_node.level == 3:
                        areatype = next(
                            (value for key, value in areatypecolumn.items() if territory_path.endswith(key)),
                            'ward'  # Default if no match found
                            )
                        tpath = territory_path +" "+ areatype
                        Territory_node.ping_node(rlevels,current_election,tpath, create=True)
                        Area = get_L4area(Territory_node.childrenoftype(areatype),spot)
                    else:
                        Area = Territory_node.value
                        areatype = next(
                            (value for key, value in areatypecolumn.items() if territory_path.endswith(key)),
                            'ward'  # Default if no match found
                            )
                        tpath = territory_path
                    print(f"__New L4 Area:{Area} of type {areatype} at {tpath}")
                    PDelectors['Area'] = Area
                    frames.append(PDelectors)

    # so if there are electors within the area(ward or division) then the Area name needs to be updated
            if len(frames) > 0:
                mainframe = pd.concat(frames)
            mainframe = mainframe.reset_index(drop=True)

            print("____Final Loadable mainframe Areas:",len(mainframe),mainframe['Area'])
        # now generate walkname labels according to a max zone size (electors) defined for the stream(election)

            label_dict = recursive_kmeans_latlon(mainframe[['Lat', 'Long']], max_cluster_size=int(SelectedElection['walksize']), MAX_DEPTH=15)


# ----- Serialise Labels

            newlabels = pd.Series(label_dict)

            unique_label_map = {}
            serial_labels = []

            for raw_label in newlabels:
                label_key = str(raw_label).strip()  # Keep structure; no .replace('-', '')

                if label_key not in unique_label_map:
                    unique_label_map[label_key] = f"K{len(unique_label_map)+1:02}"

                serial_labels.append(unique_label_map[label_key])

            # Convert to Series, matching newlabels index
            serial_label_series = pd.Series(serial_labels, index=newlabels.index)

            # 🔍 Optional: Print the mapping
            print("📌 Unique label mapping (original → serialised):")
            for k, v in unique_label_map.items():
                print(f"   {k} → {v}")

            mainframe["WalkName"] = mainframe.index.map(serial_label_series)
# K2-3-4    mainframe["WalkName"] = mainframe.index.map(newlabels)

# ---- ADD Zones for all Level 4 areas within Level 3 areas in the import

            L4groups = mainframe['Area'].unique()
            print("____L4groups:",len(mainframe),L4groups)

            zonedelectors =pd.DataFrame()
            frames = []
            for L4group in L4groups:
                maskX = mainframe['Area'] == L4group
                L4electors = mainframe[maskX]  # gets only the L4 electors in your ward/division
                print("L4Group {L4group} in {L4groups}:",len(L4electors),L4electors.columns)
                zonedelectors = add_zone_Level4(CElection['teamsize'],L4electors)
                frames.append(zonedelectors)

            if len(frames) > 0:
                zonedelectors = pd.concat(frames)
            zonedelectors.to_csv("zonedelectors.csv",sep='\t', encoding='utf-8', index=False)

            mainframe = zonedelectors.copy()

# -------- Import Data into allelectors
            print("__details of Outcoles and DQstats", Outcols,DQstats)
            DQstats.loc[Outcols.index('WalkName'),'P3'] = 1
            formdata['tabledetails'] = "Electoral Roll File "+ImportFilename+" Details"
            layeritems = get_layer_table(results[0].head(), formdata['tabledetails'])
            print("__concat of DQstats", DQstats)
            DQstats.to_csv(subending(ImportFilename,"DQ.csv"),sep='\t', encoding='utf-8', index=False)

            print(f"__concat of mainframe of length {len(mainframe)}- columns:",mainframe.columns )
            allelectors = pd.concat([allelectors, pd.DataFrame(mainframe)], ignore_index=True)
            allelectors = allelectors.reset_index(drop=True)
            allelectors.to_csv(ELECTOR_FILE,sep='\t', encoding='utf-8', index=False)

        else:
            print(f"Low fix level {fixlevel} or zero {len(allelectors)} electors to process:")


        print('_______ROUTE/normalise/exit:',ImportFilename, allelectors.columns)
        progress["percent"] = 100
        progress["status"] = "complete"
        progress["targetfile"] = ImportFilename
        progress["message"] = "load complete."

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ Exception in background_normalise:", e)
        print(tb)
        progress["percent"] = 100
        progress["status"] = "complete"
        progress["message"] = f"Error: {str(e)}"
