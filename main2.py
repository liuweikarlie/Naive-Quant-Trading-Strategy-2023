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
    def __init__(self, initial_position, initial_price,bot,stockID):
        self.stockID=stockID
        self.avg_price = initial_price
        self.highest_bid = initial_price - 0.01  # Initial bid slightly below current price
        self.lowest_ask = initial_price + 0.01  # Initial ask slightly above current price
        self.target_profit_percent = 1.0  # Target profit percentage
        self.transaction_fee_percent = 0.02/100 # Transaction fee as a percentage
        self.target_buy_price_ratio = 0.98  # Buy at 2% below the current market price
        self.transaction_fee_percent_buy=0.02
        self.bot=bot
        self.buy_price=0
        self.pnl=0
        self.sell_price=0
        self.time_1=0
        self.vwap_value=0
        self.person_pnl=0
        self.cash=0
        self.active_order_num=0
        self.flag=0
        self.initial_pnl=0
        self.sell_order={}
        self.position =0
        self.buy_order={}
        self.buy_average_price=0
        self.buy_volume=0
        self.sell_average_price=0
        self.sell_volume=0
        self.init_position=700
        self.init_share_hold=0
        self.update_position()
        self.avg_price_profit=0
        self.previous_bid_price=initial_price-0.01
        self.avg_price_pnl_highest=self.avg_price_profit
        self.buy_too_much=0
        self.too_active=0
        self.initial_pnl=0
        self.vwap=0
        self.market_condition=0
        self.update_pnl()
        self.buy_process=[]
        self.sell_process=[]
        self.stop_order={}
        self.stop_process=[]
        self.share_hold=0
        self.finished_orders = {}
        logger.debug("in the init function, {}".format(self.position))
        # active_order=self.bot.api.sendGetActiveOrder(self.bot.token_ub)['instruments'][0]['active_orders']
        # if active_order !=[]:
        #     for i in active_order:
        #         if i['direction']=='buy':
                    
        #             self.buy_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume']})
        #         elif i['direction']=='sell':
        #             self.sell_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume']})
        if self.buy_order!={}:
            self.buy_highest=max([item['price'] for item in self.buy_order.values()])
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
        try:
            record=self.bot.api.sendGetUserInfo(self.bot.token_ub)
            logger.info("sharpe: {}".format(record['sharpe']))
            logger.info("sharpe: {}".format(record['rows'][self.stockID]['pnl']))
        except Exception as e:
            logger.info("Failed to get record. Error: {}".format(e))


        
        self.avg_price = self.highest_bid
       
        self.target_profit_percent = 1.0  # Target profit percentage
        self.transaction_fee_percent = 0.01 # Transaction fee as a percentage
        self.target_buy_price_ratio = 0.99  # Buy at 2% below the current market price
        self.transaction_fee_percent_buy=0.0002
        self.bot=bot
        self.buy_price=0
        self.pnl=0
        self.sell_price=0
        self.time_1=0
        self.person_pnl=0
        self.cash=0
        self.active_order_num=0
        self.flag=0
        self.initial_pnl=0
        self.sell_order={}
        self.position =0
        self.buy_order={}
        self.buy_average_price=0
        self.buy_volume=0
        self.sell_average_price=0
        self.sell_volume=0
        self.init_position=0
        self.init_share_hold=0
        
        self.avg_price_profit=0
        self.previous_bid_price=self.highest_bid-0.01
        self.avg_price_pnl_highest=self.avg_price_profit
        self.buy_too_much=0
        self.too_active=0
        self.initial_pnl=0

        self.buy_process=[]
        self.sell_process=[]
        self.stop_order={}
        self.stop_process=[]
        self.share_hold=0
        self.finished_orders = {}
        self.vwap=0
        self.market_condition=0


    def cancel_order_item(self,order_item):
        t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
        reply=self.bot.api.sendCancel(self.bot.token_ub, self.bot.instruments[self.stockID], t, order_item['index'])
        if reply['status']=='Success':
            logger.info("cancel-this order item placed successfully.")
            if order_item['direction']==-1:
                self.position=self.position+order_item['quantity']
                self.sell_order.pop(order_item['index'])
            elif order_item['direction']==0:
                self.position=self.position+order_item['quantity']
                self.stop_order.pop(order_item['index'])
            else:
                self.buy_order.pop(order_item['index'])
        else:
            logger.info("failed to canceled order item. Error: {}".format(reply['status']))

    def cancel_order(self,order,number):
        logger.info("cancel_order")
        count=0
        traded_order=0
        copy_order=order.copy()
        for i in copy_order.values():
            t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
            reply=self.bot.api.sendCancel(self.bot.token_ub, self.bot.instruments[self.stockID], t, i['index'])
            if reply['status']=='Success':
                logger.info("cancel-this order placed successfully.")
                
                order.pop(i['index'])

                count=count+1
                if i['direction']==-1:
                    self.position=self.position+i['quantity']
                elif i['direction']==0:
                    self.position=self.position+i['quantity']

                if count==number:
                    break
            elif reply['status']=='Traded Order':
                traded_order=traded_order+1
                logger.info("failed to canceled . Error: {}, remove it from the order".format(reply['status']))
            else:
                logger.info("failed to canceled . Error: {}".format(reply['status']))
        # self.update_position()
        if traded_order==number-1:
            self.update_position()

    def check_buy_opportunity(self):
        # logger.info("check buy opportunity")
        # Calculate the bid-ask spread
        spread = self.lowest_ask - self.highest_bid

        # Assess a hypothetical condition for buying
        target_buy_price = max(self.avg_price,self.highest_bid) * self.target_buy_price_ratio
        # print(f"Buy opportunity at {target_buy_price}")

        if spread > 0 and target_buy_price <=self.highest_bid and self.flag==0 and (self.pnl>=0 or self.flag==1):
            # logger.info("spread > 0 and target_buy_price <=self.highest_bid")
            # There is an opportunity to buy
            return True
        elif self.vwap==1 :
            return True
        elif self.vwap ==1 and self.market_condition==-1:
            return True
        
        elif self.highest_bid-self.avg_price>=0.02:
            self.avg_price=self.highest_bid-0.01
            # logger.info("self.highest_bid-self.avg_price>=0.04")
            return True
        elif spread<0.03 and spread>0 and self.highest_bid-self.previous_bid_price>=0.015:
            self.avg_price=self.previous_bid_price
            # logger.info("spread<0.03 and spread>0 or self.highest_bid-self.previous_bid_price>=0.015")
            return True
        else:
            if (self.highest_bid-self.avg_price>=0.05):
                self.avg_price=self.highest_bid-0.01
            
            # logger.info("target price {}".format(target_buy_price))
            # logger.info("highest_bid {}".format(self.highest_bid))
            return False

    def place_buy_order(self):
        # Place a buy limit order

    
        logger.info("place buy order")
        spread_quantity=8

        if abs(self.vwap_value-self.highest_bid)>=0.01:
            spread_quantity=16
        

        target_buy_price = max(self.avg_price,self.buy_highest) * self.target_buy_price_ratio
        adjusted_buy_price = round(target_buy_price + (target_buy_price * self.transaction_fee_percent_buy),2)
        adjusted_buy_price=min(adjusted_buy_price,self.vwap_value-0.02)
        if abs(adjusted_buy_price-self.highest_bid)>=0.03 and self.market_condition==1:
            adjusted_buy_price=self.highest_bid-0.02
        
        if adjusted_buy_price==self.buy_price:
            return False

        
        t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)

        re=self.bot.api.sendOrder(self.bot.token_ub, self.bot.instruments[self.stockID], t, 'buy', adjusted_buy_price, spread_quantity*100)
        

        # Assume an API call or trading platform interaction to place the buy order
        if re['status']=='Success':
            # print(f"Placing buy order at {adjusted_buy_price}")
            self.buy_price=adjusted_buy_price
            # logger.debug(type(self.buy_order))
            self.buy_order[re['index']] = {
                'index': re['index'],
                'price': adjusted_buy_price,
                'quantity': spread_quantity*100,
                'direction': 1,
                'time': self.time_1
            }
            # self.flag=0
            self.buy_highest=max(self.buy_highest,adjusted_buy_price)
            self.cash=self.cash-adjusted_buy_price*100
            return True
        # elif re['status']=='Too Much Active Order':
        #     self.flag=1
            

        #     return False
        elif re['status']=='Too Much Active Order':
            if self.buy_order!={}:
                self.cancel_order(self.buy_order,1)
            elif self.sell_order!={}:
                self.cancel_order(self.sell_order,1)
            elif self.stop_order!={}:
                self.cancel_order(self.stop_order,1)
                

            logger.info("too much active order")
            return False
        else:
            # print("Unsuccess: {}".format(re['status']))
            logger.info("Failed to place buy order. Error: {}".format(re['status']))
            return False

    def check_sell_opportunity(self):
        # Calculate the bid-ask spread
        spread = self.lowest_ask - self.highest_bid

        # Assess profitability based on the spread and target profit percentage
        if  self.position>0 :
            
            # print("current_highest_sell_price: "+ str(self.current_highest_sell_price))
            target_sell_price = self.avg_price * (1 + self.target_profit_percent / self.position)
            target_sell_price=max(self.vwap_value,target_sell_price)
            # print(f"Sell opportunity at {target_sell_price}")

            if spread > 0 and target_sell_price>self.lowest_ask :
                # There is an opportunity to sell at a profit
                return True
            elif self.vwap==-1:
                # logger.info("vwap is -1, sell")
                return True
            elif self.vwap==1 and self.market_condition==1:
                return True
            elif self.lowest_ask-target_sell_price>=0.03:
                self.avg_price=self.lowest_ask
                return True
      
            elif self.highest_bid-self.previous_bid_price>=0.03:
                self.avg_price=self.highest_bid-0.01
                return True
            else:
                # logger.info("target price {}".format(target_sell_price))
                return False
        else:
            # logger.info("position is 0")
            return False
    def update_position(self):
        
        # re=self.bot.api.sendGetTrade(self.bot.token_ub,'UBIQ000')['trade_list']
        try:
            re=self.bot.api.sendGetUserInfo(self.bot.token_ub)
            if re==[]:
                self.position=0
            else:
                try:
                    active_order=self.bot.api.sendGetActiveOrder(self.bot.token_ub)['instruments'][self.stockID]['active_orders']
                    logger.info("active order: {}".format(active_order))
                    if active_order !=[]:
                        self.sell_order={}
                        self.buy_order={}
                        for i in active_order:
                            if i['direction']=='sell':
                                order = {
                                    'index': i['order_index'],
                                    'quantity': i['volume'],
                                    'price': i['order_price'],
                                    'direction': -1,
                                    'time': self.time_1
                                }
                                # self.sell_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume'],'direction':-1,'time':self.time_1})
                                self.sell_order[i['order_index']]=order
                            elif i['direction']=='buy':
                                
                                order = {
                                    'index': i['order_index'],
                                    'quantity': i['volume'],
                                    'price': i['order_price'],
                                    'direction': 1,
                                    'time': self.time_1
                                }
                                # self.sell_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume'],'direction':-1,'time':self.time_1})
                                self.buy_order[i['order_index']]=order
                        # logger.info("active order: {}".format(active_order))
                    else:
                        self.buy_order={}
                        self.sell_order={}
                    position=re['rows'][self.stockID]['share_holding']
                    self.share_hold=position
                    if self.init_position==0 and self.time_1==0:
                        self.init_position=position-len(self.sell_order)
                    if self.init_share_hold==0 and self.time_1==0:
                        self.init_share_hold=position
                        logger.info("in the update position function init share hold: {}".format(self.init_share_hold))

                    # logger.info("position: {}".format(position))
                    self.position=position

        
                
                except Exception as e:
                    
                    logger.info("Failed to update position. Error: {}".format(e))
                               
                # ti

                # me.sleep(5)
                # self.position=0
        except Exception as e:
            logger.info("Failed to update position. Error: {}".format(e))
            
            # time.sleep(5)
            # self.position=0
         
       
        
    
    def update_pnl(self):
        try:
            re=self.bot.api.sendGetUserInfo(self.bot.token_ub)
            if re==[]:
                # self.position=0
                self.avg_price_profit=0
                self.avg_price_pnl_highest=0
                
            
        
            else: 
                if (self.initial_pnl==0 and self.time_1==0) or [1 for item in self.finished_orders.values() if item['direction']==-1]==[]:
                    self.initial_pnl=re['rows'][self.stockID]['pnl']
                if self.pnl!=re['rows'][self.stockID]['pnl']:
                    logger.info("pnl changed from {} to {}".format(self.pnl,re['rows'][self.stockID]['pnl']))
                self.pnl=re['rows'][self.stockID]['pnl']
               
                if self.position!=0:
                    self.avg_price_profit=self.pnl/self.position
                    self.avg_price_pnl_highest=max(self.avg_price_profit,self.avg_price_pnl_highest)
                else:
                    self.avg_price_profit=0
                    self.avg_price_pnl_highest=0
            # logger.info("pnl: {}".format(self.pnl))
        
        except Exception as e:
            logger.info("Failed to update pnl. Error: {}".format(e))
     
       

        
    










    def place_sell_order(self,quantity):
        
        if self.position<quantity or quantity==0 or self.position==0:
            return False
        
        sell_quantity=self.position
        
            
        # target_sell_price = self.avg_price * (1 + self.target_profit_percent / self.position)
        # target_sell_price=min(target_sell_price,self.current_highest_sell_price)
        # # if target_sell_price<self.highest_bid:
        # #     target_sell_price=self.highest_bid+0.01
        # sell_price=round(target_sell_price + (target_sell_price * self.transaction_fee_percent),2)
       
        # adjusted_sell_price = max(self.highest_bid,self.buy_highest,self.vwap_value+0.01,sell_price)
        adjusted_sell_price=self.vwap_value+0.01
        if self.market_condition==1:
            adjusted_sell_price=self.vwap_value+0.02
        elif self.market_condition==-1:
            adjusted_sell_price=self.vwap_value+0.01
        


        
        # if adjusted_sell_price==self.sell_price:
        #     return False
        
        t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
        
        re=self.bot.api.sendOrder(self.bot.token_ub,self.bot.instruments[self.stockID], t, 'sell', adjusted_sell_price, sell_quantity)
        if re['status']=='Success':
        
            self.sell_price=adjusted_sell_price
            self.sell_order[re['index']]={'index':re['index'],'price':adjusted_sell_price,'quantity':sell_quantity,'direction':-1,'time':self.time_1}
            self.position=self.position-sell_quantity
            return True
        elif re['status']=='Too Much Active Order' or re['status']=='Not Enough Share':
                if re['status']=='Not Enough Share':
                    self.update_position()
                    logger.info("Failed to place sell order. Error: {}".format(re['index']))
                
                elif re['status']=='Too Much Active Order':
                    if self.buy_order!={}:
                        self.cancel_order(self.buy_order,1)
                    elif self.sell_order!={}:
                        self.cancel_order(self.sell_order,1)
                    elif self.stop_order!={}:
                        self.cancel_order(self.stop_order,1)
                
                    logger.info("too much active order")

        
                return False
        else:
            return False


        # Assume an API call or trading platform interaction to place the sell order
    
    def get_buy_price(self):
        return self.buy_price
    
    def get_sell_price(self):
        return self.sell_price
    def simulate_trade(self, new_price):
        # Simulate a trade by updating the average price and position
        if self.position>0:
            total_value_after_trade = self.position * new_price

        # Update average price
            self.avg_price = total_value_after_trade / self.position
        else:
            self.avg_price=new_price
        #self.avg_price=self.position * new_price / self.position
        if self.buy_order!={}:
            self.buy_highest=max([trade['price'] for trade in self.buy_order.values()])
        
        self.active_order_num=len(self.buy_order)+len(self.sell_order)


    def check_stop_loss(self, current_price, stop_loss_percent):
        # Check if the current price has fallen below the stop-loss threshold
        stop_loss_price = self.avg_price * (1 - stop_loss_percent / 100)
        if current_price<stop_loss_price:
            logger.info("Stop-loss triggered at current_price<stop_loss_price {}".format(current_price))
      
        elif self.avg_price_profit<self.avg_price_pnl_highest-0.01:
            logger.info("Stop-loss triggered at self.avg_price_profit<self.avg_price_pnl_highest-0.03 {}".format(self.avg_price_profit))
        return current_price < stop_loss_price or self.avg_price_profit<self.avg_price_pnl_highest-0.003 or self.position>1000 or self.pnl<-100 

    def place_stop_loss_order(self,new_price):
        # Place a market sell order to trigger the stop-loss
        # print("hi2")
        if self.buy_order!={} and self.position!=0:
           
            self.cancel_order(self.buy_order,len(self.buy_order))
  
        if self.position==0:
            logger.info("stop loss, no need, no position: {}" .format(self.position))
            return False



        if self.position > 0 and self.flag==0:
            print("hi1")
            quantity=self.position
           
           
            # logger.info("stop loss price is {}".format(new_price))
            
            t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
            re = self.bot.api.sendOrder(self.bot.token_ub, self.bot.instruments[self.stockID], t, 'sell', new_price, quantity)
            if re['status'] == 'Success':
                self.stop_order[re['index']]={'index':re['index'],'price':new_price,'quantity':quantity,'direction':0,"time":self.time_1}
                logger.info("Stop-loss order placed successfully.")
                self.position=self.position-quantity
                return True
            
           
                
            elif re['status']=='Not Enough Share':
                self.position=0
                self.update_position()
                logger.info("Failed to place stop-loss order. Error: {}".format(re['status']))
             
                
                if re['status'] == 'Success':
                    logger.info("Stop-loss order placed successfully.")
                    return True
                else:
                    logger.info("Failed to place stop-loss order. Error: {}".format(re['status']))
                    return False
            else:
            

                
                # self.update_position()
                logger.info("Failed to place stop-loss order. Error: {}".format(re['status']))
                logger.info("Failed to place sell order. Error: {}".format(re['index']))
                return False


               
        elif self.flag==1:
            

            logger.info("upward_trend ? maybe current position :{}" .format(self.position))
            
            return False
        
        else:


            logger.info("stop loss but no position: {}" .format(self.position))
            return False


    def delete_stop_order(self):
        copy_stop_order=self.stop_order.copy()
        logger.info("delete_stop_order")

        for i in copy_stop_order.values():
            if (abs(i['price']-self.highest_bid)>0.03 or abs(i['price']-self.lowest_ask)>0.021) or abs(self.time_1-i['time']>=100):
                self.cancel_order_item(i)
    

    def delete_buy_order(self):
        copy_buy_order=self.buy_order.copy()
        for i in copy_buy_order.values():
            if (abs(i['price']-self.highest_bid)>=0.06 or abs(i['price']-self.lowest_ask)>=0.06) or abs(self.time_1-i['time']>=100):
                self.cancel_order_item(i)
    
    def delete_sell_order(self):
        copy_sell_order=self.sell_order.copy()
        logger.info("delete_sell_order")
        for i in copy_sell_order.values():
            if (abs(i['price']-self.highest_bid)>=0.05 or abs(i['price']-self.lowest_ask)>=0.05) or abs(self.time_1-i['time']>=100):
                self.cancel_order_item(i)


    def orderbook_update(self,index, remain, trade_price,trade_volume,trade_index):
        if index in self.buy_order:
            direction = -1
            order = self.buy_order[index]
        elif index in self.sell_order:
            direction = 1
            order = self.sell_order[index]
        elif index in self.stop_order: 
            direction=1
            order=self.stop_order[index]
            # Handle the case where the order is not found
        else:
            return 
            

        remaining_quantity = remain

        finished_order = {
            'index': index,
            'quantity': trade_volume,
            'remaining_quantity': remaining_quantity,
            'price': trade_price,
            'direction': direction
        }

        self.finished_orders[trade_index] = finished_order

        # Update active orders with remaining quantity
        if remaining_quantity > 0:
            order['quantity'] = remaining_quantity
            if direction == -1:
                self.buy_order[index] = order
            elif direction == 1:
                if index in self.sell_order:
                    self.sell_order[index] = order
                else:
                    self.stop_order[index] = order
        else:
            # Remove from active orders if no remaining quantity
            if direction == -1:
                self.buy_order.pop(index)
            elif direction == 1:
                if index in self.sell_order:
                    self.sell_order.pop(index)
                else:
                    self.stop_order.pop(index)




    def trade_logic(self, new_bid, new_ask,high_sell,vwap,vwap_value,market_condition):
        self.vwap=vwap
        stop_loss_percent = 0.05  
        self.vwap_value=round(vwap_value,2)
        self.update_order_book(new_bid, new_ask,high_sell)
        self.market_condition=market_condition
        
        trade_history=self.bot.api.sendGetTrade(self.bot.token_ub,self.bot.instruments[self.stockID])
        if trade_history !=[]:
            logger.info("trade_history: {}".format(trade_history))
            trade_item=trade_history['trade_list']
     
            for trade_item_item in trade_item:
                self.orderbook_update(trade_item_item['order_index'],trade_item_item['remain_volume'],trade_item_item['trade_price'],trade_item_item['trade_volume'],trade_item_item['trade_index'])
            
            buy_add_position=sum([item['quantity'] for item in self.finished_orders.values() if item['direction']==-1])
            logger.info("buy_add_position: {}".format(buy_add_position))
            sell_delete_position=sum([item['quantity'] for item in self.finished_orders.values() if item['direction']==1])
            # stop_delete_position=0
            current_sell_book_position=sum([item['quantity'] for item in self.sell_order.values()])
            current_stop_book_position=sum([item['quantity'] for item in self.stop_order.values()])
            # logger.info("sell_delete_position: {}".format(sell_delete_position))
            logger.info("Holding (including in the Active book) {}".format(buy_add_position-sell_delete_position))
           
           
            self.position=self.init_position+buy_add_position-sell_delete_position-current_sell_book_position-current_stop_book_position
            logger.info("self.position: {}".format(str(self.position)+"+"+str(current_sell_book_position)+"+"+str(current_stop_book_position)+"="+str(self.share_hold)))
            self.share_hold=self.position+current_sell_book_position+current_stop_book_position
            if self.position<0:
                self.position=max(self.position,0)
                logger.info("position is negative, set it to 0")
            # logger.debug("buy_add_position {} ".format(buy_add_position))
        else:
            self.share_hold=self.position+sum(item['quantity'] for item in self.sell_order.values())+sum(item['quantity'] for item in self.stop_order.values())

        logger.info("Holding (including in the Active book) {}".format(self.share_hold))

        logger.debug("initial_pnl {}".format(self.initial_pnl))
        logger.debug("initial position {}".format(self.init_position))
        logger.debug("initial share hold {}".format(self.init_share_hold))
        # logger.debug("self.position {}".format(self.position))
        if self.position<self.share_hold:
            logger.debug("too much order in the active book")



            
        self.pnl=self.initial_pnl+sum(item['price'] * item['quantity'] *item['direction'] for item in self.finished_orders.values())+ (self.share_hold * new_ask)
        if [1 for item in self.finished_orders.values() if item['direction']==-1]==[]:
            self.update_pnl()

        logger.info("current pnl : {}".format(self.pnl))
        if self.position != 0:
            self.avg_price_pnl_highest = max(self.pnl / self.position, self.avg_price_pnl_highest)


        # logger.info("avg_price {}".format(self.avg_price))


           



        if (self.time_1%50==0):
            # logger.info("get here update position")
            self.update_pnl()
            self.update_position()
          
        
        
            
        
        
        # logger.info("current pnl : {}".format(self.pnl))
        if self.pnl>0 or self.pnl<-150:
            self.flag=0
                      
                   
        self.time_1=self.time_1+1
        # self.active_order_num=len(self.buy_order)+len(self.sell_order)
        
        # self.active_order_num=len(self.buy_order)+len(self.sell_order)
        # if self.active_order_num>=10 and self.too_active>=10:
        #     self.cancel_order(self.buy_order,1)
        #     self.cancel_order(self.sell_order,1)
        #     self.too_active=0
        # elif self.active_order_num>=10 and self.too_active<10:
        #     self.too_active=self.too_active+1
        

        if self.highest_bid-self.avg_price>=0.05:
            self.avg_price=self.highest_bid-0.01
        elif self.avg_price-self.highest_bid>=0.05:
            self.avg_price=self.highest_bid+0.01

        


        # Check for a buy opportunity
       
        
       
        
        # self.update_position()
        # logger.info("current self.avg_price : {}".format(self.avg_price))
        logger.info("positioin: {}" .format(self.position))
        if self.check_stop_loss((new_bid),stop_loss_percent) :
                print("stop_loss")
            
                if self.place_stop_loss_order((new_bid+0.01)):
                    self.simulate_trade(new_bid+0.01)
        
        if self.vwap==1 or self.time_1%5==0:
            if self.check_buy_opportunity():
                # Place a buy order
                if(self.place_buy_order()):
                    
                    self.simulate_trade(new_bid)
                    if self.buy_order!={}:
                        self.buy_highest=max([trade['price'] for trade in self.buy_order.values()])
                        
        
        # print("current self.avg_price :"+str(self.avg_price))
        if self.time_1%4==0 or (self.vwap==-1) or (self.vwap==1 and self.market_condition==1):
            
            if self.check_sell_opportunity():
                
                # self.update_position()
                
                if(self.place_sell_order(self.position)):
                    self.simulate_trade(new_ask)



        self.previous_bid_price=new_bid
        if self.position==0 and self.pnl<-30 and self.pnl>-150 and self.flag==0:
            self.flag=1
            self.avg_price=new_bid
            self.avg_price_pnl_highest=0

      
        self.delete_buy_order()
        self.delete_sell_order()    
        self.delete_stop_order()
        # logger.info("current time_id {}".format(self.time_1))
        # logger.info("self finished_order {}".format(self.finished_orders))
        # logger.info("self buy_order {}".format(self.buy_order))
        # logger.info("self sell_order {}".format(self.sell_order))
        # logger.info("self stop_order {}".format(self.stop_order))

        



        if self.pnl>=800 or (self.pnl<=-80 and vwap==-1) or self.market_condition==-100:
            if self.buy_order!={}:
                self.cancel_order(self.buy_order,len(self.buy_order))
            
            if self.sell_order!={}:
                self.cancel_order(self.sell_order,len(self.sell_order))
            
            
                
                # self.cancel_order(self.sell_order,len(self.sell_order))
            # a,b=self.update_position()
            # self.position=b
            price=self.vwap_value
            if self.market_condition==-100:
                price=self.highest_bid
            
            if self.position>0:
                quantity=self.position
               
                if self.pnl<=-80:
                    price=self.highest_bid-0.01
                re = self.bot.api.sendOrder(self.bot.token_ub, self.bot.instruments[self.stockID], t, 'sell', price, quantity)
                
                if re['status'] == 'Success':
                    self.stop_order[re['index']]={'index':re['index'],'price':new_bid,'quantity':quantity,'direction':0,'time':self.time_1}
                    self.position=self.position-quantity
                    logger.info("Stop-loss order placed successfully. in the logic")
                    return (True, self.pnl)
                    
                elif re['status']=="Not Enough Share":
                    logger.info("stop loss processing in the queue in the logic in the logic, quit")
                    return (False,self.pnl)
                
                else:
                    logger.info("Failed to place stop-loss order. Error: {}".format(re['status']))
                    return (False,self.pnl)
            
                    
            else:
                return (True, self.pnl)
        else:
            return (False,self.pnl)
      

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
        super().__init__(username, password)
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
        # self.instruments=['UBIQ000']
        self.day = 0
        self.trade_status={}
        self.time=0
        self.MarketMaker1=None
        self.stockID_1=0
        self.reply_stock1=False

        self.MarketMaker2=None
        self.stockID_2=0
        self.reply_stock2=False
        self.vwap={}
        self.change_vwap={}
        self.pnl=0
        self.win=False
        self.current_vwap_change=0
        self.change=False
        # active_order_re=self.api.sendGetTrade(self.token_ub)
        # if active_order_re['status']=='Success':
        #     for i in active_order_re['']:
        #         self.trade_status[i['instrument']]=i
        # self.current_cash=997321.46
        # LOB = self.api.sendGetLimitOrderBook(self.token_ub, self.instruments[self.stockID])
        
        
        # if LOB["status"] == "Success":
        #     self.MarketMaker=MarketMaker(0,LOB['lob']['bidprice'][0],self,stockID)
        
    def bod(self):
        
        
        self.vwap={}
        self.change_vwap={}
        self.pnl=0
        self.win=False
        self.current_vwap_change=0
        self.change=False
        self.MarketMaker1=None
        self.reply_stock1=False

        
        LOB = self.api.sendGetLimitOrderBook(self.token_ub, self.instruments[self.stockID_1])
        
        if LOB["status"] == "Success":
            self.MarketMaker1=MarketMaker(0,LOB['lob']['bidprice'][0],self,self.stockID_1)
        

        # LOB = self.api.sendGetLimitOrderBook(self.token_ub, self.instruments[self.stockID_2])
        
        # if LOB["status"] == "Success":
        #     self.MarketMaker2=MarketMaker(0,LOB['lob']['bidprice'][0],self,self.stockID_2)
    def calculate(self,stockID_1):
        LOB = self.api.sendGetLimitOrderBook(self.token_ub, self.instruments[stockID_1])
        if LOB["status"] == "Success":
            vwap=(LOB['lob']['bidprice'][0]*LOB['lob']['askvolume'][0]+LOB['lob']['askprice'][0]*LOB['lob']['bidvolume'][0])/(LOB['lob']['askvolume'][0]+LOB['lob']['bidvolume'][0])
            if self.instruments[stockID_1] in self.vwap:
                self.vwap[self.instruments[stockID_1]].append(vwap)
                self.change_vwap[self.instruments[stockID_1]].append(vwap-self.vwap[self.instruments[stockID_1]][-2])
            else:
                self.vwap[self.instruments[stockID_1]]=[vwap]
                self.change_vwap[self.instruments[stockID_1]]=[0]
    def work(self): 
        # current_LOB_list=[]
        # stockID = random.randint(0, len(self.instruments) - 1)

        # if self.time<10:
        #     for i in range(len(self.instruments)):
        #         self.calculate(i)
            
            
        
        



            
        if self.MarketMaker1==None:
            self.bod()

        LOB = self.api.sendGetLimitOrderBook(self.token_ub, self.instruments[self.stockID_1])
        if LOB["status"] == "Success":
            vwap=(LOB['lob']['bidprice'][0]*LOB['lob']['askvolume'][0]+LOB['lob']['askprice'][0]*LOB['lob']['bidvolume'][0])/(LOB['lob']['askvolume'][0]+LOB['lob']['bidvolume'][0])
            if self.instruments[self.stockID_1] in self.vwap:
                self.vwap[self.instruments[self.stockID_1]].append(vwap)
                self.change_vwap[self.instruments[self.stockID_1]].append(vwap-self.vwap[self.instruments[self.stockID_1]][-2])
            else:
                self.vwap[self.instruments[self.stockID_1]]=[vwap]
                self.change_vwap[self.instruments[self.stockID_1]]=[0]
                
           
            market_condition=0
            if sum(self.change_vwap[self.instruments[self.stockID_1]][-3:])>0:
                market_condition=1
            elif sum(self.change_vwap[self.instruments[self.stockID_1]][-3:])<0:
                market_condition=-1
            else:
                market_condition=0
            


            if len(self.change_vwap)>50:
                market_evaluation=sum(self.change_vwap[self.instruments[self.stockID_1]][-50:])
                logger.debug("market_evaluation: {}".format(market_evaluation))
                if market_evaluation<0 and self.pnl<10:
                    self.change=True
                    market_condition=-100
            if self.reply_stock1==False :
                if (self.change_vwap[self.instruments[self.stockID_1]][-1]>0 and sum(self.change_vwap[self.instruments[self.stockID_1]][-2:])>0):
                    value=self.MarketMaker1.trade_logic(LOB['lob']['bidprice'][0],LOB['lob']['askprice'][0],LOB['lob']['askprice'][9],1,vwap,market_condition)
                elif self.change_vwap[self.instruments[self.stockID_1]][-1]<0:
                    value=self.MarketMaker1.trade_logic(LOB['lob']['bidprice'][0],LOB['lob']['askprice'][0],LOB['lob']['askprice'][9],-1,vwap,market_condition)
                else:
                    value=self.MarketMaker1.trade_logic(LOB['lob']['bidprice'][0],LOB['lob']['askprice'][0],LOB['lob']['askprice'][9],0,vwap,market_condition)

                self.reply_stock1=value[0]
                self.pnl=value[1]
                
                # logger.info("vwap_change: {}".format(self.change_vwap[self.instruments[self.stockID_1]]))
                # logger.info("vwap: {}".format(self.vwap[self.instruments[self.stockID_1]][-10:]))
                # self.reply_stock1=True
                if self.win==True:
                    self.reply_stock1=False
                
            elif self.reply_stock1==True and self.pnl>300:
                if self.time%50==0:
                    try:
                        re=self.api.sendGetUserInfo(self.token_ub)
                        logger.info("here1")
                        if re!=[]:
                            logger.info("here2")
                            # self.position=0
                            pnl=re['rows'][self.stockID_1]['pnl']
                            trade_value=re['row'][self.stockID_1]['trade_value']
                            if pnl<400:
                                self.reply_stock1=False
                            if trade_value<200000 and self.change_vwap[self.instruments[self.stockID_1]][-1]>0 and self.change_vwap[self.instruments[self.stockID_1]][-2]>=0:
                                self.reply_stock1=False
                                self.win=True
                            
                        active_order=self.api.sendGetActiveOrder(self.token_ub)['instruments'][self.stockID_1]['active_orders']
                        logger.info("active order: {}".format(active_order))
                    except Exception as e:
                        # self.win=True
                        # self.reply_stock1=False
                        logger.debug("Failed to update pnl. Error: {}".format(e))

            else:
                self.change=True
                logger.info("stop here, negative profit")

        self.time=self.time+1
        if self.change==True:
            self.stockID_1=self.stockID_1+1
            if self.stockID_1>28:
                self.stockID_1=0
            self.bod()
            self.change=False



          
            
                
           
           
        




           
    def eod(self):
        self.MarketMaker1.reset()
        self.MarketMaker1=None
        
        # re=self.api.sendGetActiveOrder(self.token_ub)['instruments'][0]['active_orders']
        # if re !=[]:
        #     logger.debug("sendGetActiveOrder: {}".format(re))
        
        
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
        logger.debug("Order: id {}, status: {}".format(response['index'],response['status']))
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
        # logger.info("Work Time: {}".format(t))
        # logger.info("Work S Time: {}".format(s))
        if t < SimTimeLen - 30:
           
            bot.work()
    bot.eod()
    bot.day += 1
bot.final()
