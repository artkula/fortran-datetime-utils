!> DateUtils module - Handles date operations and calculations
!> @author Improved by Artem
!> @date February 2025
module DateUtils
    implicit none
    private
    public :: GetDayOfWeek, IsLeapYear, ValidateDate, FormatDate
    
    !> Days of the week array
    character(len=9), dimension(0:6), parameter :: DAYS_OF_WEEK = (/ &
        'Sunday   ', 'Monday   ', 'Tuesday  ', 'Wednesday', &
        'Thursday ', 'Friday   ', 'Saturday ' /)
    
    !> Month names array
    character(len=9), dimension(12), parameter :: MONTH_NAMES = (/ &
        'January  ', 'February ', 'March    ', 'April    ', &
        'May      ', 'June     ', 'July     ', 'August   ', &
        'September', 'October  ', 'November ', 'December ' /)
    
    !> Days in each month (non-leap year)
    integer, dimension(12), parameter :: DAYS_IN_MONTH = &
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

contains
    !> Calculate the day of week using Zeller's congruence algorithm
    !> @param input_year Input year (4 digits)
    !> @param month Month (1-12)
    !> @param day Day (1-31)
    !> @return The name of the day
    function GetDayOfWeek(input_year, month, day) result(dayName)
        integer, intent(in) :: input_year, month, day
        character(len=9) :: dayName
        integer :: h, q, m, k, j, dow, year
        
        ! Validate input date
        if (.not. ValidateDate(input_year, month, day)) then
            dayName = 'Invalid  '
            return
        end if
        
        ! Zeller's congruence algorithm
        q = day
        if (month <= 2) then
            m = month + 12
            year = input_year - 1
        else
            m = month
            year = input_year
        end if
        
        k = mod(year, 100)
        j = year / 100
        
        h = mod(q + ((13*(m+1))/5) + k + (k/4) + (j/4) - (2*j), 7)
        
        ! Convert to 0-6 range (Sunday = 0)
        dow = mod(h + 5 + 1, 7)
        
        dayName = DAYS_OF_WEEK(dow)
    end function GetDayOfWeek
    
    !> Check if a year is a leap year
    !> @param year The year to check
    !> @return .true. if leap year, .false. otherwise
    function IsLeapYear(year) result(isLeap)
        integer, intent(in) :: year
        logical :: isLeap
        
        isLeap = (mod(year, 4) == 0 .and. mod(year, 100) /= 0) .or. (mod(year, 400) == 0)
    end function IsLeapYear
    
    !> Validate a date (year, month, day)
    !> @param year The year (4 digits)
    !> @param month The month (1-12)
    !> @param day The day (1-31 depending on month)
    !> @return .true. if valid date, .false. otherwise
    function ValidateDate(year, month, day) result(isValid)
        integer, intent(in) :: year, month, day
        logical :: isValid
        integer :: maxDays
        
        ! Check basic ranges
        if (year < 1 .or. month < 1 .or. month > 12 .or. day < 1) then
            isValid = .false.
            return
        end if
        
        ! Get maximum days for the month
        maxDays = DAYS_IN_MONTH(month)
        
        ! Adjust February for leap years
        if (month == 2 .and. IsLeapYear(year)) then
            maxDays = 29
        end if
        
        ! Check if day is valid for the month
        isValid = (day <= maxDays)
    end function ValidateDate
    
    !> Format a date as YYYY-MM-DD
    !> @param year The year (4 digits)
    !> @param month The month (1-12)
    !> @param day The day (1-31)
    !> @return Formatted date string
    function FormatDate(year, month, day) result(formattedDate)
        integer, intent(in) :: year, month, day
        character(len=10) :: formattedDate
        character(len=2) :: monthStr, dayStr
        character(len=4) :: yearStr
        
        write(yearStr, '(I4)') year
        write(monthStr, '(I2.2)') month
        write(dayStr, '(I2.2)') day
        
        formattedDate = yearStr // '-' // monthStr // '-' // dayStr
    end function FormatDate
    
    !> Get the name of a month
    !> @param month Month number (1-12)
    !> @return Month name
    function GetMonthName(month) result(monthName)
        integer, intent(in) :: month
        character(len=9) :: monthName
        
        if (month >= 1 .and. month <= 12) then
            monthName = MONTH_NAMES(month)
        else
            monthName = 'Invalid  '
        end if
    end function GetMonthName
end module DateUtils