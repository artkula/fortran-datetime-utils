!> Displays date, time, and day of week with improved formatting and error handling
!> @author Improved by Artem
!> @date February 2025
program Packing
    use DateUtils    ! Must be first since DateTimeUtils depends on it
    use DateTimeUtils
    implicit none

    type(DateTime) :: currentDateTime
    integer :: status
    character(len=12) :: formattedTime
    character(len=10) :: formattedDate
    character(len=12) :: timezoneStr

    ! Get current date and time
    status = GetDateTime(currentDateTime)

    ! Check for errors
    if (status /= 0) then
        print *, 'Error: Could not retrieve current date and time'
        stop
    end if

    ! Format date and time
    formattedDate = FormatDate(currentDateTime%year, currentDateTime%month, currentDateTime%day)
    formattedTime = FormatTime(currentDateTime%hour, currentDateTime%minute, &
                                currentDateTime%second, currentDateTime%millisecond)
    timezoneStr = GetTimezoneInfo(currentDateTime%timezone)

    ! Print header
    print *, '=========================================='
    print *, '           DATE AND TIME INFO            '
    print *, '=========================================='

    ! Print formatted information
    print *, 'Current Date: ', formattedDate
    print *, 'Day of Week:  ', trim(currentDateTime%dayOfWeek)
    print *, 'Current Time: ', trim(formattedTime)
    print *, 'Time Zone:    ', trim(timezoneStr)
    print *, '=========================================='

    ! Additional information
    if (IsLeapYear(currentDateTime%year)) then
        print *, 'Note: This is a leap year'
    end if

    ! Calculate days until end of year
    block
        type(DateTime) :: endOfYear
        real :: daysLeft

        ! Set up end of year date
        endOfYear = currentDateTime
        endOfYear%month = 12
        endOfYear%day = 31
        endOfYear%hour = 23
        endOfYear%minute = 59
        endOfYear%second = 59
        endOfYear%millisecond = 999

        ! Calculate days left
        daysLeft = TimeDifference(currentDateTime, endOfYear) / 86400.0

        print *, 'Days remaining in the year: ', daysLeft
    end block

    print *, '=========================================='

end program Packing