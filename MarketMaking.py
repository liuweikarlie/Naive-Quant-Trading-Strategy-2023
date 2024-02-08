
import logging
import time

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
        self.transaction_fee_percent = 0.02  # Transaction fee as a percentage
        self.target_buy_price_ratio = 0.98  # Buy at 2% below the current market price
        self.bot=bot
        self.buy_price=0
        self.sell_price=0
        self.time_1=0
        self.active_order_num=0
        self.flag=0
        self.sell_order=[]
        self.position =0
        self.update_position()
        self.buy_order=[]
        active_order=self.bot.api.sendGetActiveOrder(self.bot.token_ub)['instruments'][0]['active_orders']
        if active_order !=[]:
            for i in active_order:
                if i['direction']=='buy':
                    
                    self.buy_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume']})
                elif i['direction']=='sell':
                    self.sell_order.append({'index':i['order_index'],'price':i['order_price'],'quantity':i['volume']})
            if self.buy_order!=[]:
                self.buy_highest=max([trade['price'] for trade in self.buy_order])
            else:
                self.buy_highest=0
        else: 
            self.buy_highest=0


    def update_order_book(self, bid, ask):
        self.highest_bid = bid
        self.lowest_ask = ask
    

    def too_much_active_order_cancel_order(self,order,number):
        if order!=[]:
            cancel_order=reversed(order)[:number]
            for i in cancel_order:
                t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
                reply=self.bot.api.sendCancel(self.bot.token_ub, 'UBIQ000', t, i['index'])
                if reply['status']=='Success':
                    logger.info("cancel-this order placed successfully.")
                    
                    order.remove(i)
                else:
                    logger.info("failed to canceled . Error: {}".format(reply['status']))

    def check_buy_opportunity(self):
        # Calculate the bid-ask spread
        spread = self.lowest_ask - self.highest_bid

        # Assess a hypothetical condition for buying
        target_buy_price = self.avg_price * self.target_buy_price_ratio
        # print(f"Buy opportunity at {target_buy_price}")

        if spread > 0 and target_buy_price < self.highest_bid and self.active_order_num<10:
            
            # There is an opportunity to buy
            return True
        else:
            return False

    def place_buy_order(self):
        # Place a buy limit order
        target_buy_price = self.avg_price * self.target_buy_price_ratio
        adjusted_buy_price = round(target_buy_price + (target_buy_price * self.transaction_fee_percent),2)
        if adjusted_buy_price==self.buy_price:
            return False
        t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)

        re=self.bot.api.sendOrder(self.bot.token_ub, 'UBIQ000', t, 'buy', adjusted_buy_price, 100)
        

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
                    self.too_much_active_order_cancel_order(self.buy_order,len(self.buy_order)-1)
                if self.sell_order!=[]:
                    self.too_much_active_order_cancel_order(self.sell_order,len(self.sell_order)-1)


                
                return False
        else:
         
            return False

    def check_sell_opportunity(self):
      
        spread = self.lowest_ask - self.highest_bid

        # Assess profitability based on the spread and target profit percentage
        if  self.position>0 and self.active_order_num<10:
            target_sell_price = self.avg_price * (1 + self.target_profit_percent / self.position)
            # print(f"Sell opportunity at {target_sell_price}")

            if spread > 0 and target_sell_price>self.lowest_ask:
                # There is an opportunity to sell at a profit
                return True
            else:
                return False
        else:
            return False
    def update_position(self):
        
        # re=self.bot.api.sendGetTrade(self.bot.token_ub,'UBIQ000')['trade_list']
        re=self.bot.api.sendGetUserInfo(self.bot.token_ub)
        if re==[]:
            self.position=0
        else:
            self.position=re['rows'][0]['share_holding']
            if self.position!=0:
                self.avg_price=re['rows'][0]['position']/self.position
            else:
                self.buy_highest=self.highest_bid
                self.avg_price=self.highest_bid
        logger.info("position: {}".format(self.position))

    def reset_sell_price(self,sell_quantity):
        # newprice=self.avg_price * (1 + self.target_profit_percent / self.position)
        
        if self.buy_highest<self.highest_bid:
            target_sell_price=self.highest_bid
            adjusted_sell_price=round(target_sell_price + (target_sell_price * self.transaction_fee_percent),2)
        

            t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
            
            re=self.bot.api.sendOrder(self.bot.token_ub, 'UBIQ000', t, 'sell', adjusted_sell_price, sell_quantity)
            if re['status']=='Success':
                # self.position=self.position-100
                self.sell_price=adjusted_sell_price
                
                self.sell_order.append({'index':re['index'],'price':adjusted_sell_price,'quantity':sell_quantity})
                return True
        
            else:
                # print("Unsuccess: {}".format(re['status']))

                return False
        
        else:
            self.too_much_active_order_cancel_order(self.buy_order,len(self.buy_order)-1)









    def place_sell_order(self):
        sell_quantity=min(self.position,300)
        target_sell_price = self.avg_price * (1 + self.target_profit_percent / self.position)
        # if target_sell_price<self.highest_bid:
        #     target_sell_price=self.highest_bid+0.01
        adjusted_sell_price = max(round(target_sell_price + (target_sell_price * self.transaction_fee_percent),2),self.buy_highest)
        if adjusted_sell_price==self.sell_price:
            return False
        t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
        
        re=self.bot.api.sendOrder(self.bot.token_ub, 'UBIQ000', t, 'sell', adjusted_sell_price, sell_quantity)
        if re['status']=='Success':
            # self.position=self.position-100
            self.sell_price=adjusted_sell_price
            
            self.sell_order.append({'index':re['index'],'price':adjusted_sell_price,'quantity':sell_quantity})
            return True
        elif re['status']=='Too Much Active Order' or re['status']=='Not Enough Share':
                if re['status']=='Not Enough Share':
                    # self.update_position()
                    print("adjusted_sell_price: "+ str(adjusted_sell_price))
                    self.reset_sell_price(sell_quantity)
                elif re['status']=='Too Much Active Order':
                    # if self.buy_order!=[]:
                    #     self.cancel_order(self.buy_order,2)
                    if self.sell_order!=[]:
                        self.too_much_active_order_cancel_order(self.sell_order,2)

          
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
        return current_price < stop_loss_price

    def place_stop_loss_order(self,new_price):
        # Place a market sell order to trigger the stop-loss
        if self.position > 0:
            self.too_much_active_order_cancel_order(self.buy_order,len(self.buy_order))
            t = ConvertToSimTime_us(self.bot.start_time, self.bot.time_ratio, self.bot.day, self.bot.running_time)
            re = self.bot.api.sendOrder(self.bot.token_ub, 'UBIQ000', t, 'sell', new_price-0.01, self.position)
            if re['status'] == 'Success':
                logger.info("Stop-loss order placed successfully.")
                return True
            
            else:
                logger.info("Failed to place stop-loss order. Error: {}".format(re['status']))
                return False
        else:
            return False




    def trade_logic(self, new_bid, new_ask):
        # Update the order book with new bid and ask prices
        stop_loss_percent = 0.5  # Example: 2% stop-loss
        self.update_order_book(new_bid, new_ask)
        if self.time_1%3==0:
            self.update_position()
        trade_history=self.bot.api.sendGetTrade(self.bot.token_ub,'UBIQ000')
        if trade_history !=[]:
            trade_item=trade_history['trade_list']
            for i in trade_item:
                
                self.buy_order=[order for order in self.buy_order if order['index']!=i['order_index'] and i['remain_volume']!=0]
                self.sell_order=[order for order in self.sell_order if order['index']!=i['order_index'] and i['remain_volume']!=0]
        
        if self.time_1%5==0 and self.active_order_num>=10:
            if self.buy_order!=[]:
                self.too_much_active_order_cancel_order(self.buy_order,1)
            if self.sell_order!=[]:
                self.too_much_active_order_cancel_order(self.sell_order,1)
                      
                   
        self.time_1=self.time_1+1
        self.active_order_num=len(self.buy_order)+len(self.sell_order)

        


        # Check for a buy opportunity
        if self.check_buy_opportunity():
            # Place a buy order
            if(self.place_buy_order()):

            # Simulate a trade (update average price and position)
                self.simulate_trade(new_bid)
        
        if self.buy_order!=[]:
            self.buy_highest=max([trade['price'] for trade in self.buy_order])


        print(self.buy_highest)
        # Check for a sell opportunity
        if self.check_sell_opportunity():
            # Place a sell order
            if(self.place_sell_order()):

            # Simulate a trade (update average price and position)
                self.simulate_trade(new_ask)


        if self.check_stop_loss(self.highest_bid+self.lowest_ask/2, stop_loss_percent) :
            # Place a stop-loss sell order
            if self.place_stop_loss_order(self.highest_bid+self.lowest_ask/2):
                # Simulate a trade (update average price and position)
                self.simulate_trade(new_ask)

  