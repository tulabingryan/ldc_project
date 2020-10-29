import random


#V2G Charge/Discharge Profile Generator  V1.0, questions shinson@pecanstreet.org
#copyright 2020 Pecan Street Inc.


#Charge Profile Paramaters
chargePower = 5000 #requested charge power
chargeType = 'discharge'  # set this value to charge or discharge 
chargeDuration = 40 #minutes

#Vehicle Parameters
totalkWh = 40.0 # battery capacity, 40kWh for Nissan Leaf, nominal
minimumSOC = 5.0 #discharge vehicle minimum
vehicleSOC = 70.0 # vehicle state of charge. 0-100
batteryEff =.99 #battery charge/discharge efficiecy (may be a tad high) 
currentkWh = vehicleSOC*totalkWh/100
#Charge Station Parameters
chargerMax = 10000.00 #maximum charger hardware power typically 10kW for split phase/residential, 30kW+ for commercial. Vehicles may limit.
chargerEff = 0.95 #Typical maximum
chargerOffset = 40.0 #power used to maintain electronics in charger while charging
file = 'demofile5.txt'
#profile output file
f = open(file,"w")  
f.write("minute,watts,soc\n")
f.close()

#if charge

#Determine if battery can handle duration of charge specified without >100% SOC
if chargeType == 'charge':
    if chargePower >= chargerMax:
        chargePower = chargerMax    #most charging systems we've worked with ignore power requests over maximum and cap at maximum
    currentkWh = vehicleSOC*totalkWh/100
    print('Current vehicle energy',currentkWh,'\n')
    batteryPower = chargePower*batteryEff*chargerEff
    print('Battery input power after losses',batteryPower,'\n')
    energyIn = (chargeDuration*batteryPower)/(1000*60)
    print('Requested energy in:',energyIn,'\n')
    maximumIn = totalkWh - totalkWh*vehicleSOC/100
    print('Maximum energy into vehicle with starting SOC:',maximumIn,'\n')
    if maximumIn >= energyIn:
        print('Generate time charge profile file, not shortened')
        for x in range(chargeDuration):
            flutterPower = random.randint(-50,50)
            batteryPower = (chargePower+flutterPower)*batteryEff*chargerEff  #chargers we've used typically set AC line power for charge, battery power is less
            currentkWh = currentkWh + batteryPower/(1000*60)
            vehicleSOC = round(100*currentkWh/totalkWh,2)
            textWrite = str(x) + ',' + str(chargePower+flutterPower+chargerOffset) + ',' + str(vehicleSOC)+ '\n'
            f = open(file,"a")
            f.write(textWrite)
            f.close()
    else:
        print('Maximum in: ',maximumIn,'kWh...\n')
        hoursCharging = maximumIn/(chargePower/1000) # determines number of charge hours
        print('Hours of charging to max:  ', hoursCharging,'\n')
        newDuration = int(60*hoursCharging)
        print('Minutes of charging to get to max: ',newDuration,'\n')  #finds duration minutes, rounds down. 
        print('Generate time charge profile file, shortened')
        for x in range(newDuration):  
            flutterPower = random.randint(-50,50)
            batteryPower = (chargePower+flutterPower)*batteryEff*chargerEff
            currentkWh = currentkWh + batteryPower/(1000*60)
            vehicleSOC = round(100*currentkWh/totalkWh,2)
            textWrite = str(x) + ',' + str(chargePower+flutterPower+chargerOffset) + ',' + str(vehicleSOC)+ '\n'
            f = open(file,"a")
            f.write(textWrite)
            f.close()   #note will likely end at something less than 100% typically between 95-99%, cars rarely fast charge to 100%
        
#if discharge
if chargeType == 'discharge':
    if chargePower >= chargerMax:
        chargePower = chargerMax
    if vehicleSOC > minimumSOC:
        availablekWh = (vehicleSOC-minimumSOC)*totalkWh/100  # determine the kWh available.
        print('Current vehicle energy for discharge',availablekWh,'\n')
        outputPower = chargePower*batteryEff*chargerEff  #power exported to the grid after losses.  So for a 90% eff system and a 1kW request .9kW to battery or .9kW to grid.  
        print('Typical output power after losses',outputPower,'\n')
        energyOut = chargePower*chargeDuration/(1000*60)
        print('Requested kWh out of vehicle',energyOut,'\n')
        maximumOut = availablekWh
        if energyOut <= maximumOut:
            print('Generate time discharge profile file, not shortend')
            for x in range(chargeDuration):
                flutterPower = random.randint(-50,50)
                batteryPower = -1*chargePower
                currentkWh = currentkWh + batteryPower/(1000*60)
                vehicleSOC = round(100*currentkWh/totalkWh,2)
                textWrite = str(x)+',' + str(batteryPower*batteryEff*chargerEff+flutterPower-chargerOffset)+','+str(vehicleSOC)+'\n'
                f = open(file,"a")
                f.write(textWrite)
                f.close()
        else:
            hoursDischarging = availablekWh/(chargePower/1000)
            print('Current vehicle energy for discharge',availablekWh,'\n')
            print('Hours of discharging to min:  ', hoursDischarging,'\n')
            newDuration = int(60*hoursDischarging)
            print('Minutes of discharging to get to min: ',newDuration,'\n')  #finds duration minutes, rounds down. 
            print('Generate time discharge profile, shortented')
            for x in range(newDuration):
                flutterPower = random.randint(-50,50)
                batteryPower = -1*chargePower
                currentkWh = currentkWh + batteryPower/(1000*60)
                vehicleSOC = round(100*currentkWh/totalkWh,2)
                textWrite = str(x)+',' + str(batteryPower*batteryEff*chargerEff+flutterPower-chargerOffset)+','+str(vehicleSOC)+'\n'
                f = open(file,"a")
                f.write(textWrite)
                f.close()

    if vehicleSOC < minimumSOC:
            f = open(file,"a")
            f.write('discharge not allowed, starting SOC too low')
            f.close()

f = open(file,"r")
print(f.read())





    