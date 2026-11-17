# 1. Retrieve all successful bookings:
select * from ola where Booking_Status = 'Success';

#2. Find the average ride distance for each vehicle type:
select round(avg(ride_distance),2) as Avg_ride_distance from ola ;

#3. Get the total number of cancelled rides by customers:
select count(Booking_Status) as cancelled_rides_by_customers 
from ola where Booking_Status = 'Canceled by Customer';

#4. List the top 5 customers who booked the highest number of rides:
select Customer_ID,
       count(*) as Book_Rides 
from ola group by 1 order by 2 desc limit 5;

#5. Get the number of rides cancelled by drivers due to personal and car-related issues:
select count(*) as 'rides cancelled by drivers due to personal and car-related issues' from ola where Canceled_Rides_by_Driver ='Personal & Car related issue';

#6. Find the maximum and minimum driver ratings for Prime Sedan bookings:
select
    max(cast(Driver_Ratings as decimal(3,1))) as Max_Rating,
    min(cast(Driver_Ratings as decimal(3,1))) as Min_Rating
from ola
where Vehicle_Type = 'Prime Sedan'
  and Driver_Ratings <> 'No Rating';

#7. Retrieve all rides where payment was made using UPI:
select count(*) from ola where Payment_Method='UPI'; 

#8. Find the average customer rating per vehicle type:
select Vehicle_Type, 
	   round(avg(Customer_Rating),2) Ratings 
from ola group by 1 order by 2;

#9. Calculate the total booking value of rides completed successfully:
select count(*) from ola where Booking_Status='Success';

#10. List all incomplete rides along with the reason
select Incomplete_Rides_Reason from ola where Incomplete_Rides_Reason <>'Not Applicable';

#11. Which vehicle type has the highest cancellation rate?
select Vehicle_Type, 
       count(*) Total_booking,
       sum(booking_Status like 'Canceled%') as Total_cancelled,
       round(100*sum(booking_Status like 'Canceled%')/count(*),1) as cancel_pct
from ola group by 1 order by 4 desc;

#12. What are the top 5 peak demand hours, for driver allocation?
select Hour,
       count(*) as Booking 
from ola group by 1 order by 2 desc limit 5;

#13. Which pickup areas have the most “Driver Not Found” bookings (unmet demand)?
select Pickup_Location,
       count(*) driver_not_found
from ola where Booking_Status = 'Driver Not Found'
group by 1 order by 2 desc;

#14. How much booking value was lost to failed bookings?
select Booking_Status,
       count(*) as Total_Ride,
       sum(Booking_Value) as Total_Lost_value
from ola where Booking_Status <> 'Success' group by 1;

#15. Which vehicle type earns the most per kilometre?
select Vehicle_Type,
       round(sum(Booking_Value)/sum(Ride_Distance),2) as value_per_KM
from ola where Booking_Status = 'Success' group by 1 order by 2 desc;

#16. How many customers are repeat customers (more than one successful ride)?
select count(*) as Repeat_Customers from (
select customer_id 
from ola where booking_status='Success' group by 1 having count(*)>1) t;

#17. What share of successful rides does each payment method have?
select payment_method,
       count(*) as ride,
       round(100*count(*)/sum(count(*)) over(),1) as pct
from ola where Booking_Status = 'Success' group by 1 order by 2 desc;

#18. Which 3 pickup locations bring the most revenue?
select Pickup_Location,
       sum(booking_value) as Revenue
from ola where booking_status='success' group by 1 order by 2 desc limit 3;

#19. Which vehicle types have the most low-rated drivers (rating below 3.5)?
select Vehicle_Type,
       sum(Driver_Ratings<3.5) low_rated,
       count(Driver_Ratings) as Rated_Ride 
from ola group by 1 order by 2 desc;

#20. Which days had the highest revenue?
select Weekday,
       sum(booking_value) Revenue       
from ola where  Booking_Status = 'Success' group by 1 order by 2 desc;




