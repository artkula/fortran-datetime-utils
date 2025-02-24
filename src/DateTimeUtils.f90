!> DateTimeUtils module - Handles date and time operations
!> @author Improved by Artem
!> @date February 2025
module DateTimeUtils
    use DateUtils
    implicit none
    private
    public :: GetDateTime, FormatTime, GetTimezoneInfo, TimeDifference
    
    !> Date time container type
    type, public :: DateTime
        integer :: year        !< Year (4 digits)
        integer :: month       !< Month (1-12)
        integer :: day         !< Day (1-31)
        integer :: hour        !< Hour (0-23)
        integer :: minute      !< Minute (0-59)
        integer :: second      !< Second (0-59)
        integer :: millisecond !< Millisecond (0-999)
        character(len=9) :: dayOfWeek  !< Day of week (Monday, Tuesday, etc.)
        integer :: timezone    !< Minutes from UTC
    end type DateTime

contains
    !> Get the current date and time
    !> @param dateTime Output DateTime structure
    !> @return Error code (0 if successful)
    function GetDateTime(dateTime) result(status)
        type(DateTime), intent(out) :: dateTime
        integer :: status
        integer :: values(8)
        
        ! Initialize status to success
        status = 0
        
        ! Get date and time information from system
        call date_and_time(VALUES=values)
        
        ! Fill DateTime structure
        dateTime%year = values(1)
        dateTime%month = values(2)
        dateTime%day = values(3)
        dateTime%timezone = values(4)  ! Minutes from UTC
        dateTime%hour = values(5)
        dateTime%minute = values(6)
        dateTime%second = values(7)
        dateTime%millisecond = values(8)
        
        ! Validate date
        if (.not. ValidateDate(dateTime%year, dateTime%month, dateTime%day)) then
            status = 1
            return
        end if
        
        ! Get day of week
        dateTime%dayOfWeek = GetDayOfWeek(dateTime%year, dateTime%month, dateTime%day)
    end function GetDateTime
    
    !> Format time as HH:MM:SS.mmm
    !> @param hour Hour (0-23)
    !> @param minute Minute (0-59) 
    !> @param second Second (0-59)
    !> @param millisecond Millisecond (0-999) - optional
    !> @return Formatted time string
    function FormatTime(hour, minute, second, millisecond) result(formattedTime)
        integer, intent(in) :: hour, minute, second
        integer, intent(in), optional :: millisecond
        character(len=12) :: formattedTime
        character(len=2) :: hourStr, minuteStr, secondStr
        character(len=3) :: millisecondStr
        
        write(hourStr, '(I2.2)') hour
        write(minuteStr, '(I2.2)') minute
        write(secondStr, '(I2.2)') second
        
        if (present(millisecond)) then
            write(millisecondStr, '(I3.3)') millisecond
            formattedTime = hourStr // ':' // minuteStr // ':' // secondStr // '.' // millisecondStr
        else
            formattedTime = hourStr // ':' // minuteStr // ':' // secondStr
        end if
    end function FormatTime
    
    !> Get timezone information as string
    !> @param minutesFromUTC Minutes from UTC
    !> @return Formatted timezone string (e.g., "UTC+01:00")
    function GetTimezoneInfo(minutesFromUTC) result(timezoneStr)
        integer, intent(in) :: minutesFromUTC
        character(len=12) :: timezoneStr
        integer :: hours, minutes
        character(len=1) :: sign
        character(len=2) :: hourStr, minuteStr
        
        ! Determine sign
        if (minutesFromUTC < 0) then
            sign = '-'
            hours = abs(minutesFromUTC) / 60
            minutes = abs(minutesFromUTC) - (hours * 60)
        else
            sign = '+'
            hours = minutesFromUTC / 60
            minutes = minutesFromUTC - (hours * 60)
        end if
        
        write(hourStr, '(I2.2)') hours
        write(minuteStr, '(I2.2)') minutes
        
        timezoneStr = 'UTC' // sign // hourStr // ':' // minuteStr
    end function GetTimezoneInfo
    
    !> Calculate time difference in seconds between two DateTime objects
    !> @param dateTime1 First DateTime
    !> @param dateTime2 Second DateTime
    !> @return Time difference in seconds (dateTime2 - dateTime1)
    function TimeDifference(dateTime1, dateTime2) result(diffSeconds)
        type(DateTime), intent(in) :: dateTime1, dateTime2
        real :: diffSeconds
        integer :: days1, days2
        real :: seconds1, seconds2
        
        ! Convert both dates to days + seconds
        days1 = DaysFromDate(dateTime1%year, dateTime1%month, dateTime1%day)
        days2 = DaysFromDate(dateTime2%year, dateTime2%month, dateTime2%day)
        
        seconds1 = dateTime1%hour * 3600 + dateTime1%minute * 60 + dateTime1%second + dateTime1%millisecond / 1000.0
        seconds2 = dateTime2%hour * 3600 + dateTime2%minute * 60 + dateTime2%second + dateTime2%millisecond / 1000.0
        
        ! Calculate difference
        diffSeconds = (days2 - days1) * 86400.0 + (seconds2 - seconds1)
    end function TimeDifference
    
    !> Helper function to convert a date to days since a reference date
    !> Using Jan 1, 1900 as reference date
    function DaysFromDate(year, month, day) result(days)
        integer, intent(in) :: year, month, day
        integer :: days
        integer :: y, m, d
        integer :: i
        
        ! Algorithm to convert date to days (simplified)
        y = year - 1900
        days = y * 365
        
        ! Add leap days
        days = days + (y / 4) - (y / 100) + (y / 400)
        
        ! Add days for months
        do i = 1, month - 1
            days = days + DAYS_IN_MONTH(i)
            
            ! Adjust for February in leap years
            if (i == 2 .and. IsLeapYear(year)) then
                days = days + 1
            end if
        end do
        
        ! Add days in current month
        days = days + day - 1
    end function DaysFromDate
end module DateTimeUtils