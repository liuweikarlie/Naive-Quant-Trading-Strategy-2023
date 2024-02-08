import requests
import socket
import json
import time
import logging
import random


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def ConvertToSimTime_us(start_time, time_ratio, day, running_time):
    return (time.time() - start_time - (day - 1) * running_time) * time_ratio

class MarketMaker:
    def __init__(self, initial_position, initial_price,bot):
        self.avg_price = initial_price
        self.highest_bid = initial_price - 0.01  # Initial bid slightly below current price
        self.lowest_ask = initial_price + 0.01  # Initial ask slightly above current price
        self.target_profit_percent = 1.0  # Target profit percentage
        self.transaction_fee_percent = 0.01 # Transaction fee as a percentage
        self.target_buy_price_ratio = 0.98  # Buy at 2% below the current market price
        self.transaction_fee_percent_buy=0.02
        self.bot=bot
        self.buy_price=0
        self.pnl=0
        self.sell_price=0
        self.time_1=0
        self.active_order_num=0
        self.flag=0
        self.sell_order=[]
        self.position =0
        self.update_position()
        self.buy_order=[]
        self.avg_price_profit=0
        self.previous_bid_price=0
        self.avg_price_pnl_highest=self.avg_price_profit
        # active_order=self.bot.api.sendGetActiveOrder(self.bot.token_ub)['instruments'][0]['active_orders']
        # if active_order !=[]:
        #     for i in active_order:
        #         if i['direction']=='buy':
                    
        #             self.buy_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume']})
        #         elif i['direction']=='sell':
        #             self.sell_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume']})
        if self.buy_order!=[]:
            self.buy_highest=max([trade['price'] for trade in self.buy_order])
        else:
            self.buy_highest=0



    def update_order_book(self, bid, ask,high_sell_price):
        # Update the order book with new bid and ask prices
        if(self.avg_price==0):
            self.avg_price=bid
        if (self.previous_bid_price==0):
            self.previous_bid_price=bid
        self.highest_bid = bid
        self.lowest_ask = ask
        self.current_highest_sell_price=high_sell_price
    
    def reset(self):
        self.highest_bid=0
        self.lowest_ask=0
        self.avg_price=0
        self.target_profit_percent = 1.0  # Target profit percentage
        self.transaction_fee_percent = 0.01 # Transaction fee as a percentage
        self.target_buy_price_ratio = 0.98  # Buy at 2% below the current market price
        self.transaction_fee_percent_buy=0.02
        self.bot=bot
        self.buy_price=0
        self.pnl=0
        self.sell_price=0
        self.time_1=0
        self.active_order_num=0
        self.flag=0
        self.sell_order=[]
        self.position =0
        self.previous_bid_price=0
        self.buy_order=[]
        self.avg_price_profit=0
        self.avg_price_pnl_highest=self.avg_price_profit


    def cancel_order(self,order,number):
        count=0
        for i in order:
            t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
            reply=self.bot.api.sendCancel(self.bot.token_ub, 'UBIQ000', t, i['index'])
            if reply['status']=='Success':
                logger.info("cancel-this order placed successfully.")
                
                order.remove(i)

                count=count+1
                if count==number:
                    break
            else:
                logger.info("failed to canceled . Error: {}".format(reply['status']))
        self.update_position()

    def check_buy_opportunity(self):
        # Calculate the bid-ask spread
        spread = self.lowest_ask - self.highest_bid

        # Assess a hypothetical condition for buying
        target_buy_price = self.avg_price * self.target_buy_price_ratio
        # print(f"Buy opportunity at {target_buy_price}")

        if spread > 0 and target_buy_price <=self.highest_bid :
            
            # There is an opportunity to buy
            return True
        elif spread<=0.02 and spread>0 and self.highest_bid-self.previous_bid_price>=0.02:
            self.avg_price=self.previous_bid_price
            return True
        else:
            logger.info("target price {}".format(target_buy_price))
            logger.info("highest_bid {}".format(self.highest_bid))
            return False

    def place_buy_order(self):
        # Place a buy limit order
        if self.active_order_num>=10:
            self.cancel_order(self.buy_order,1)
        spread_quantity=int((self.lowest_ask-self.highest_bid)//0.01)
        # print("spread_quantity: "+str(spread_quantity))
        if spread_quantity>=1:
            spread_quantity=1
        elif spread_quantity<=0:
            spread_quantity=2
        target_buy_price = max(self.avg_price,self.buy_highest-0.02) * self.target_buy_price_ratio
        adjusted_buy_price = round(target_buy_price + (target_buy_price * self.transaction_fee_percent_buy),2)
        if adjusted_buy_price==self.buy_price:
            return False
        t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)

        re=self.bot.api.sendOrder(self.bot.token_ub, 'UBIQ000', t, 'buy', adjusted_buy_price, spread_quantity*100)
        

        # Assume an API call or trading platform interaction to place the buy order
        if re['status']=='Success':
            # print(f"Placing buy order at {adjusted_buy_price}")
            self.buy_price=adjusted_buy_price
            self.buy_order.append({'index':re['index'],'price':adjusted_buy_price,'quantity':100})
            # self.flag=0
            self.buy_highest=max(self.buy_highest,adjusted_buy_price)
            return True
        # elif re['status']=='Too Much Active Order':
        #     self.flag=1
            

        #     return False
        elif re['status']=='Too Much Active Order':
                if self.buy_order!=[]:
                    self.cancel_order(self.buy_order,len(self.buy_order))
                if self.sell_order!=[]:
                    self.cancel_order(self.sell_order,len(self.sell_order))


                
                return False
        else:
            # print("Unsuccess: {}".format(re['status']))
            return False

    def check_sell_opportunity(self):
        # Calculate the bid-ask spread
        spread = self.lowest_ask - self.highest_bid

        # Assess profitability based on the spread and target profit percentage
        if  self.position>0 :
            
            # print("current_highest_sell_price: "+ str(self.current_highest_sell_price))
            target_sell_price = self.avg_price * (1 + self.target_profit_percent / self.position)
            # print(f"Sell opportunity at {target_sell_price}")

            if spread > 0 and target_sell_price>self.lowest_ask :
                # There is an opportunity to sell at a profit
                return True
            elif spread >0.03:
                self.avg_price=self.highest_bid-0.03
                return True
            elif self.highest_bid-self.previous_bid_price>=0.04:
                return True
            else:
                return False
        else:
            return False
    def update_position(self):
        
        # re=self.bot.api.sendGetTrade(self.bot.token_ub,'UBIQ000')['trade_list']
        try:
            re=self.bot.api.sendGetUserInfo(self.bot.token_ub)
            if re==[]:
                self.position=0
            else:
                active_order=self.bot.api.sendGetActiveOrder(self.bot.token_ub)['instruments'][0]['active_orders']
                if active_order !=[]:
                    for i in active_order:
                        if i['direction']=='sell':
                            self.sell_order=[]
                            self.sell_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume']})
                        elif i['direction']=='buy':
                            self.buy_order=[]
                            self.buy_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume']})
                position=re['rows'][0]['share_holding']
                self.position=position-sum([trade['quantity'] for trade in self.sell_order])
        
                
            
        
            logger.info("position: {}".format(position))
        
        except Exception as e:
            logger.info("Failed to get position. Error: {}".format(e))
            


    
    def update_pnl(self):
        try:
            re=self.bot.api.sendGetUserInfo(self.bot.token_ub)
            if re==[]:
                self.position=0
                self.avg_price_profit=0
                self.avg_price_pnl_highest=0
                
            
        
            else: 
                self.pnl=re['rows'][0]['pnl']
                if self.position!=0:
                    self.avg_price_profit=self.pnl/self.position
                    self.avg_price_pnl_highest=max(self.avg_price_profit,self.avg_price_pnl_highest)
        catch:
            logger.info("Failed to get pnl. Error: {}".format(e))
            self.pnl=self.

        
    
    def reset_sell_price(self,sell_quantity,sell_price):
        # newprice=self.avg_price * (1 + self.target_profit_percent / self.position)
        if self.active_order_num>=10:
            self.cancel_order(self.buy_order,1)


        if self.buy_highest<self.highest_bid:
            target_sell_price=self.highest_bid
            adjusted_sell_price=round(target_sell_price + (target_sell_price * self.transaction_fee_percent),2)
        

            t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
            
            re=self.bot.api.sendOrder(self.bot.token_ub, 'UBIQ000', t, 'sell', adjusted_sell_price, sell_quantity)
            if re['status']=='Success':
                # self.position=self.position-100
                self.sell_price=adjusted_sell_price
                
                self.sell_order.append({'index':re['index'],'price':adjusted_sell_price,'quantity':sell_quantity})
                
        
           
       

        else:
            self.cancel_order(self.buy_order,len(self.buy_order)-1)
            









    def place_sell_order(self,quantity):
        
        if self.position<quantity and quantity==0 and self.position==0:
            return False
        sell_quantity=quantity
        target_sell_price = self.avg_price * (1 + self.target_profit_percent / self.position)
        target_sell_price=min(target_sell_price,self.current_highest_sell_price)
        # if target_sell_price<self.highest_bid:
        #     target_sell_price=self.highest_bid+0.01
        sell_price=round(target_sell_price + (target_sell_price * self.transaction_fee_percent),2)
        adjusted_sell_price = max(sell_price,self.buy_highest)
        if adjusted_sell_price==self.sell_price:
            return False
        # if self.highest_bid-self.previous_bid_price>=0.04:
        #     adjusted_sell_price=self.previous_bid_price-0.01
        t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
        
        re=self.bot.api.sendOrder(self.bot.token_ub, 'UBIQ000', t, 'sell', adjusted_sell_price, sell_quantity)
        if re['status']=='Success':
            # self.position=self.position-100
            self.sell_price=adjusted_sell_price
            
            self.sell_order.append({'index':re['index'],'price':adjusted_sell_price,'quantity':sell_quantity})
            self.update_position()
            return True
        elif re['status']=='Too Much Active Order' or re['status']=='Not Enough Share':
                if re['status']=='Not Enough Share':
                    # self.update_position()
                    logger.info("Failed to place sell order. Error: {}".format(re['index']))
                    # print("avg_price: "+ str(self.avg_price))
                    # print("adjusted_sell_price: "+ str(sell_price))
                    # print("self.buy_highest: "+ str(self.buy_highest))
                    # self.reset_sell_price(sell_quantity,sell_price)
                elif re['status']=='Too Much Active Order':
                    # if self.buy_order!=[]:
                    #     self.cancel_order(self.buy_order,2)
                    if self.sell_order!=[]:
                        self.cancel_order(self.buy_order,1)

          
        else:
            # print("Unsuccess: {}".format(re['status']))

            return False


        # Assume an API call or trading platform interaction to place the sell order
    
    def get_buy_price(self):
        return self.buy_price
    
    def get_sell_price(self):
        return self.sell_price
    def simulate_trade(self, new_price):
        # Simulate a trade by updating the average price and position
        if self.position>0:
            total_value_before_trade = self.position * self.avg_price
            total_value_after_trade = self.position * new_price

        # Update average price
            self.avg_price = total_value_after_trade / self.position
        else:
            self.avg_price=new_price
        #self.avg_price=self.position * new_price / self.position
        if self.buy_order!=[]:
            self.buy_highest=max([trade['price'] for trade in self.buy_order])
        
        self.active_order_num=len(self.buy_order)+len(self.sell_order)


    def check_stop_loss(self, current_price, stop_loss_percent):
        # Check if the current price has fallen below the stop-loss threshold
        stop_loss_price = self.avg_price * (1 - stop_loss_percent / 100)
        if current_price<stop_loss_price:
            logger.info("Stop-loss triggered at current_price<stop_loss_price {}".format(current_price))
        elif self.pnl<-0.001:
            logger.info("Stop-loss triggered at self.pnl<-0.001 {}".format(self.pnl))
        elif self.avg_price_profit<0:
            logger.info("Stop-loss triggered at self.avg_price_profit<0 {}".format(self.avg_price_profit))
        elif self.avg_price_profit<self.avg_price_pnl_highest-0.01:
            logger.info("Stop-loss triggered at self.avg_price_profit<self.avg_price_pnl_highest-0.01 {}".format(self.avg_price_profit))
        return current_price < stop_loss_price or self.pnl<-0.001 or self.avg_price_profit<0 or self.avg_price_profit<self.avg_price_pnl_highest-0.01

    def place_stop_loss_order(self,new_price):
        # Place a market sell order to trigger the stop-loss
        if self.position > 0:
            self.cancel_order(self.buy_order,len(self.buy_order))
            t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
            re = self.bot.api.sendOrder(self.bot.token_ub, 'UBIQ000', t, 'sell', round(new_price-0.01,2), self.position)
            if re['status'] == 'Success':
                logger.info("Stop-loss order placed successfully.")
                return True
            
            elif re['status']=='Too Much Active Order':

                logger.info("Failed to place stop-loss order. Error: {}".format(re['status']))
                self.cancel_order(self.sell_order,len(self.sell_order))
                self.cancel_order(self.buy_order,len(self.buy_order))
                t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
                re = self.bot.api.sendOrder(self.bot.token_ub, 'UBIQ000', t, 'sell', new_price-0.01, self.position)
                if re['status'] == 'Success':
                    logger.info("Stop-loss order placed successfully.")
                    return True
                else:
                    return False
            else:
                self.update_position()
                logger.info("Failed to place stop-loss order. Error: {}".format(re['status']))
                logger.info("Failed to place sell order. Error: {}".format(re['index']))
                return False


               
        else:
            return False




    def trade_logic(self, new_bid, new_ask,high_sell):
        stop_loss_percent = 0.2  
        self.update_order_book(new_bid, new_ask,high_sell)
        
        trade_history=self.bot.api.sendGetTrade(self.bot.token_ub,'UBIQ000')
        if trade_history !=[]:
            trade_item=trade_history['trade_list']
            for i in trade_item:
                original_buy_order=self.buy_order
                self.buy_order=[order for order in original_buy_order if order['index']!=i['order_index'] and i['remain_volume']!=0]
                self.sell_order=[order for order in self.sell_order if order['index']!=i['order_index'] and i['remain_volume']!=0]
                proceed_buy_order=[item for item in original_buy_order if item not in self.buy_order]
                sum_buy_quantity=sum([order['quantity'] for order in proceed_buy_order])
                self.position=self.position+sum_buy_quantity
        # elif self.time_1%5==0 and self.active_order_num>=10:
        #     if self.buy_order!=[]:
        #         self.cancel_order(self.buy_order,1)
        #     if self.sell_order!=[]:
        #         self.cancel_order(self.sell_order,1)
        self.update_pnl()
                      
                   
        self.time_1=self.time_1+1
        self.active_order_num=len(self.buy_order)+len(self.sell_order)

        


        # Check for a buy opportunity
       
        
       
        
        # self.update_position()
        print("current self.avg_price :"+str(self.avg_price))
        if self.check_stop_loss((new_bid+new_ask)/2, stop_loss_percent) :
                print("stop_loss")
                if self.place_stop_loss_order((new_bid+new_ask)/2):
                    self.position=self.position-self.position
                    self.simulate_trade(new_ask)
        if self.check_buy_opportunity():
            # Place a buy order
            if(self.place_buy_order()):
                
                self.simulate_trade(new_bid)
                if self.buy_order!=[]:
                    self.buy_highest=max([trade['price'] for trade in self.buy_order])
        
        # print("current self.avg_price :"+str(self.avg_price))
        if self.check_sell_opportunity():
            
            # self.update_position()
            if(self.place_sell_order(self.position)):
                self.position=self.position-self.position
                self.simulate_trade(new_ask)

            # if self.position >100:
            #     iteration_round=0
            #     if self.position%100==0:
            #         iteration_round=self.position//100
            #     else:
            #         iteration_round=(self.position//100)+1
                    
            #     for i in range(iteration_round):
            #         sell_quantity=100
            #         if iteration_round-1==i:
            #             sell_quantity=self.position%100
            #             if sell_quantity==0:
            #                 break
            #         if(self.place_sell_order(sell_quantity)):

            #             self.simulate_trade(new_ask)

            # elif self.position>0:
            #     if(self.place_sell_order(self.position)):

            #         self.simulate_trade(new_ask)
        self.previous_bid_price=new_bid
      

  
      

class BotsClass:
    def __init__(self, username, password):
        self.username = username
        self.password = password
    def login(self):
        pass
    def init(self):
        pass
    def bod(self):
        pass
    def work(self):
        pass
    def eod(self):
        pass
    def final(self):
        pass

class BotsDemoClass(BotsClass):
    def __init__(self, username, password):
        super().__init__(username, password);
        self.api = InterfaceClass("https://trading.competition.ubiquant.com")
    def login(self):
        response = self.api.sendLogin(self.username, self.password)
        if response["status"] == "Success":
            self.token_ub = response["token_ub"]
            logger.info("Login Success: {}".format(self.token_ub))
        else:
            logger.info("Login Error: ", response["status"])
    def GetInstruments(self):
        response = self.api.sendGetInstrumentInfo(self.token_ub)
        if response["status"] == "Success":
            self.instruments = []
            for instrument in response["instruments"]:
                self.instruments.append(instrument["instrument_name"])
            logger.info("Get Instruments: {}".format(self.instruments))
    def init(self):
        response = self.api.sendGetGameInfo(self.token_ub)
        if response["status"] == "Success":
            self.start_time = response["next_game_start_time"]
            self.running_days = response["next_game_running_days"]
            self.running_time = response["next_game_running_time"]
            self.time_ratio = response["next_game_time_ratio"]
        self.GetInstruments()
        self.instruments=['UBIQ000']
        self.day = 0
        self.trade_status={}
        self.time=0
        self.MarketMaker=None
        # active_order_re=self.api.sendGetTrade(self.token_ub)
        # if active_order_re['status']=='Success':
        #     for i in active_order_re['']:
        #         self.trade_status[i['instrument']]=i
        # self.current_cash=997321.46
        LOB = self.api.sendGetLimitOrderBook(self.token_ub, 'UBIQ000')
        
        if LOB["status"] == "Success":
            self.MarketMaker=MarketMaker(0,LOB['lob']['bidprice'][0],self)
        
    def bod(self):
        LOB = self.api.sendGetLimitOrderBook(self.token_ub, 'UBIQ000')
        
        if LOB["status"] == "Success":
            self.MarketMaker=MarketMaker(0,LOB['lob']['bidprice'][0],self)
              
    def work(self): 
        # current_LOB_list=[]
        # stockID = random.randint(0, len(self.instruments) - 1)
        

        LOB = self.api.sendGetLimitOrderBook(self.token_ub, 'UBIQ000')
        if LOB["status"] == "Success":
            # logger.info("Get bid: {}, ask :{}".format(LOB['lob']['bidprice'][0],LOB['lob']['askprice'][0]))
            self.MarketMaker.trade_logic(LOB['lob']['bidprice'][0],LOB['lob']['askprice'][0],LOB['lob']['askprice'][9])
        
        # if self.time%3==0:
        #     re=self.api.sendGetActiveOrder(self.token_ub)['instruments'][0]['active_orders']
        #     if re !=[]:
        #         logger.debug("sendGetActiveOrder: {}".format(re))
        # self.time=self.time+1
                


            # buy_price=self.MarketMaker.get_buy_price()
            # logger.info("buy_price: {}".format(buy_price))
            # sell_price=self.MarketMaker.get_sell_price()
            # logger.info("sell_price: {}".format(sell_price))
            # logger.info("positioin: {}".format(self.MarketMaker.position))
            # logger.info("avg_price: {}".format(self.MarketMaker.avg_price))

          
            
                
           
           
        




           
    def eod(self):
        self.MarketMaker.reset()
        # re=self.api.sendGetActiveOrder(self.token_ub)['instruments'][0]['active_orders']
        # if re !=[]:
        #     logger.debug("sendGetActiveOrder: {}".format(re))
        pass
        
    def final(self):
        pass





class InterfaceClass:
    def __init__(self, domain_name):
        self.domain_name = domain_name
        self.session = requests.Session()
    def sendLogin(self, username, password):
        url = self.domain_name + "/api/Login"
        data = {
            "user": username,
            "password": password
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response
    
    def sendGetGameInfo(self, token_ub): 
        url = self.domain_name + "/api/TradeAPI/GetGAmeInfo"

    def sendOrder(self, token_ub, instrument, localtime, direction, price, volume):
        logger.debug("Order: Instrument: {}, Direction:{}, Price: {}, Volume:{}".format(instrument, direction, price, volume))
        url = self.domain_name + "/api/TradeAPI/Order"
        data = {
            "token_ub": token_ub,
            "user_info": "NULL",
            "instrument": instrument,
            "localtime": localtime,
            "direction": direction,
            "price": price,
            "volume": volume,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        logger.debug("Order: status: {}".format(response['status']))
        return response

    def sendCancel(self, token_ub, instrument, localtime, index):
        logger.debug("Cancel: Instrument: {}, index:{}".format(instrument, index))
        url = self.domain_name + "/api/TradeAPI/Cancel"
        data = {
            "token_ub": token_ub,
            "user_info": "NULL",
            "instrument": instrument,
            "localtime": 0,
            "index": index
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        logger.debug("Cancel: status: {}".format(response['status']))
        return response

    def sendGetLimitOrderBook(self, token_ub, instrument):
        # logger.debug("GetLimitOrderBOok: Instrument: {}".format(instrument))
        url = self.domain_name + "/api/TradeAPI/GetLimitOrderBook"
        data = {
            "token_ub": token_ub,
            "instrument": instrument
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    def sendGetUserInfo(self, token_ub):
        logger.debug("GetUserInfo: ")
        url = self.domain_name + "/api/TradeAPI/GetUserInfo"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    def sendGetGameInfo(self, token_ub): # 获取比赛信息
        logger.debug("GetGameInfo: ")
        url = self.domain_name + "/api/TradeAPI/GetGameInfo"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    def sendGetInstrumentInfo(self, token_ub):
        logger.debug("GetInstrumentInfo: ")
        url = self.domain_name + "/api/TradeAPI/GetInstrumentInfo"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    def sendGetTrade(self, token_ub, instrument):
        logger.debug("GetTrade: Instrment: {}".format(instrument))
        url = self.domain_name + "/api/TradeAPI/GetTrade"
        data = {
            "token_ub": token_ub,
            "instrument_name": instrument
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response

    def sendGetActiveOrder(self, token_ub):
        logger.debug("GetActiveOrder: ")
        url = self.domain_name + "/api/TradeAPI/GetActiveOrder"
        data = {
            "token_ub": token_ub,
        }
        response = self.session.post(url, data=json.dumps(data)).json()
        return response




bot = BotsDemoClass("", "")
bot.login()
bot.init()
SimTimeLen = 14400
endWaitTime = 300
while True:
    if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) < SimTimeLen:
        break
    else:
        bot.day += 1

while bot.day <= bot.running_days:
    while True:
        if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) > -900:
            break
    bot.bod()
    now = round(ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time))
    for s in range(now, SimTimeLen + endWaitTime):
        while True:
            if ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time) >= s:
                break
        t = ConvertToSimTime_us(bot.start_time, bot.time_ratio, bot.day, bot.running_time)
        logger.info("Work Time: {}".format(t))
        # logger.info("Work S Time: {}".format(s))
        if t < SimTimeLen - 30:
            # if s %2==0:
            bot.work()
    bot.eod()
    bot.day += 1
bot.final()
